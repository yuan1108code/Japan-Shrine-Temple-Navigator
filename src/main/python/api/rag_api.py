"""
RAG (Retrieval-Augmented Generation) API 端點
結合向量搜尋和 LLM 生成，提供智慧問答功能
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..services.vector_db import VectorDatabase, VectorSearchService, VectorDBConfig
from ..core.embeddings import EmbeddingManager


logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """RAG 系統配置"""
    model_name: str = "gpt-3.5-turbo"
    max_context_length: int = 4000
    max_search_results: int = 5
    similarity_threshold: float = 0.7
    temperature: float = 0.7
    max_tokens: int = 800
    system_prompt: str = """你是福井縣的旅遊助手。請根據提供的地點資訊回答使用者的問題。

回答要求：
1. 使用繁體中文回答
2. 基於提供的資訊回答，不要編造不存在的資訊
3. 如果資訊不足，請誠實說明
4. 提供具體、實用的旅遊建議
5. 回答要親切、專業"""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "max_context_length": self.max_context_length,
            "max_search_results": self.max_search_results,
            "similarity_threshold": self.similarity_threshold,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt
        }


@dataclass
class RAGResponse:
    """RAG 回應資料結構"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float
    query: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "confidence_score": self.confidence_score,
            "query": self.query
        }


class RAGService:
    """RAG 問答服務"""
    
    def __init__(self, vector_db: VectorDatabase, config: Optional[RAGConfig] = None):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not available. Install with: pip install openai")
        
        self.vector_db = vector_db
        self.search_service = VectorSearchService(vector_db)
        self.config = config or RAGConfig()
        
        # 設定 OpenAI 客戶端
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.openai_client = openai.OpenAI(api_key=api_key)
        
        logger.info("RAG service initialized")
    
    def _retrieve_context(self, query: str) -> tuple[List[Dict[str, Any]], float]:
        """檢索相關文檔"""
        try:
            # 使用向量搜尋找到相關地點
            search_results = self.search_service.semantic_search(
                query=query,
                max_results=self.config.max_search_results
            )
            
            if not search_results:
                return [], 0.0
            
            # 計算平均相似度分數作為信心度
            avg_confidence = sum(result['similarity_score'] for result in search_results) / len(search_results)
            
            # 格式化搜尋結果
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    "location_id": result['location_id'],
                    "name": result['metadata'].get('name', '未知地點'),
                    "category": result['metadata'].get('category', '未分類'),
                    "content": result['content'],
                    "similarity_score": result['similarity_score'],
                    "tags": result['metadata'].get('tags', [])
                }
                formatted_results.append(formatted_result)
            
            return formatted_results, avg_confidence
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return [], 0.0
    
    def _build_context_text(self, search_results: List[Dict[str, Any]]) -> str:
        """構建上下文文本"""
        if not search_results:
            return "沒有找到相關的地點資訊。"
        
        context_parts = []
        context_parts.append("相關地點資訊：\n")
        
        for i, result in enumerate(search_results, 1):
            location_info = f"""
{i}. 地點：{result['name']} (類別：{result['category']})
   相關度：{result['similarity_score']:.2f}
   詳細資訊：{result['content']}
   標籤：{', '.join(result['tags']) if result['tags'] else '無'}
"""
            context_parts.append(location_info)
        
        full_context = "\n".join(context_parts)
        
        # 限制上下文長度
        if len(full_context) > self.config.max_context_length:
            full_context = full_context[:self.config.max_context_length] + "...\n(內容已截斷)"
        
        return full_context
    
    def _generate_answer(self, query: str, context: str) -> str:
        """生成回答"""
        try:
            # 構建提示
            user_prompt = f"""
上下文資訊：
{context}

使用者問題：{query}

請根據上述資訊回答使用者的問題。如果資訊不足以回答問題，請說明需要更多資訊。
"""
            
            messages = [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 調用 OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "抱歉，生成回答時發生錯誤，請稍後再試。"
    
    def ask(self, query: str) -> RAGResponse:
        """處理問答請求"""
        try:
            logger.info(f"Processing query: {query}")
            
            # 1. 檢索相關文檔
            search_results, confidence = self._retrieve_context(query)
            
            # 2. 構建上下文
            context_text = self._build_context_text(search_results)
            
            # 3. 生成回答
            answer = self._generate_answer(query, context_text)
            
            # 4. 構建回應
            response = RAGResponse(
                answer=answer,
                sources=search_results,
                confidence_score=confidence,
                query=query
            )
            
            logger.info(f"Query processed successfully, confidence: {confidence:.2f}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return RAGResponse(
                answer="抱歉，處理您的問題時發生錯誤，請稍後再試。",
                sources=[],
                confidence_score=0.0,
                query=query
            )
    
    def ask_about_location(self, location_id: str, question: str) -> RAGResponse:
        """針對特定地點提問"""
        try:
            # 獲取地點上下文
            location_context = self.search_service.get_location_context(location_id)
            
            if not location_context:
                return RAGResponse(
                    answer="抱歉，找不到指定的地點資訊。",
                    sources=[],
                    confidence_score=0.0,
                    query=question
                )
            
            # 構建上下文
            context_text = f"""
地點資訊：
名稱：{location_context['metadata'].get('name', '未知地點')}
類別：{location_context['metadata'].get('category', '未分類')}
詳細描述：{location_context['full_text']}
"""
            
            # 生成回答
            answer = self._generate_answer(question, context_text)
            
            # 構建來源資訊
            sources = [{
                "location_id": location_id,
                "name": location_context['metadata'].get('name', '未知地點'),
                "category": location_context['metadata'].get('category', '未分類'),
                "content": location_context['full_text'][:500] + "..." if len(location_context['full_text']) > 500 else location_context['full_text'],
                "similarity_score": 1.0,
                "tags": location_context['metadata'].get('tags', [])
            }]
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence_score=1.0,
                query=question
            )
            
        except Exception as e:
            logger.error(f"Error asking about location {location_id}: {e}")
            return RAGResponse(
                answer="抱歉，處理您的問題時發生錯誤。",
                sources=[],
                confidence_score=0.0,
                query=question
            )
    
    def get_recommendations(self, preferences: Dict[str, Any]) -> RAGResponse:
        """根據偏好推薦地點"""
        try:
            # 構建推薦查詢
            query_parts = []
            
            if preferences.get('category'):
                query_parts.append(f"類別：{preferences['category']}")
            
            if preferences.get('interests'):
                interests = preferences['interests']
                if isinstance(interests, list):
                    query_parts.append(f"興趣：{', '.join(interests)}")
                else:
                    query_parts.append(f"興趣：{interests}")
            
            if preferences.get('location_type'):
                query_parts.append(f"地點類型：{preferences['location_type']}")
            
            query = " ".join(query_parts) if query_parts else "推薦景點"
            
            # 使用 RAG 系統處理推薦
            response = self.ask(f"請推薦適合的景點：{query}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return RAGResponse(
                answer="抱歉，生成推薦時發生錯誤。",
                sources=[],
                confidence_score=0.0,
                query="推薦請求"
            )


class RAGAPIHandler:
    """RAG API 處理器 - 提供 FastAPI 整合"""
    
    def __init__(self, vector_db_path: str, config: Optional[RAGConfig] = None):
        # 初始化向量資料庫
        db_config = VectorDBConfig(db_path=vector_db_path)
        self.vector_db = VectorDatabase(db_config)
        
        # 初始化 RAG 服務
        self.rag_service = RAGService(self.vector_db, config)
        
        logger.info("RAG API handler initialized")
    
    async def handle_question(self, query: str) -> Dict[str, Any]:
        """處理一般問題"""
        response = self.rag_service.ask(query)
        return response.to_dict()
    
    async def handle_location_question(self, location_id: str, question: str) -> Dict[str, Any]:
        """處理地點相關問題"""
        response = self.rag_service.ask_about_location(location_id, question)
        return response.to_dict()
    
    async def handle_recommendations(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """處理推薦請求"""
        response = self.rag_service.get_recommendations(preferences)
        return response.to_dict()
    
    def get_service_stats(self) -> Dict[str, Any]:
        """獲取服務統計"""
        db_stats = self.vector_db.get_collection_stats()
        return {
            "database_stats": db_stats,
            "config": self.rag_service.config.to_dict()
        }


# 工具函數
def create_rag_service(vector_db_path: str, config_path: Optional[str] = None) -> RAGService:
    """創建 RAG 服務實例"""
    # 載入配置
    config = RAGConfig()
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # 創建向量資料庫
    db_config = VectorDBConfig(db_path=vector_db_path)
    vector_db = VectorDatabase(db_config)
    
    return RAGService(vector_db, config)


if __name__ == "__main__":
    # 測試 RAG 服務
    logging.basicConfig(level=logging.INFO)
    
    # 檢查環境變數
    if not os.getenv('OPENAI_API_KEY'):
        print("請設定 OPENAI_API_KEY 環境變數")
        exit(1)
    
    try:
        # 創建測試配置
        config = RAGConfig(
            model_name="gpt-3.5-turbo",
            max_search_results=3,
            temperature=0.7
        )
        
        # 初始化服務（需要先有向量資料庫）
        db_config = VectorDBConfig(db_path="./data/vector_db")
        vector_db = VectorDatabase(db_config)
        rag_service = RAGService(vector_db, config)
        
        # 測試問答
        test_queries = [
            "福井有哪些著名的神社？",
            "請推薦適合家庭旅遊的景點",
            "福井的美食有哪些特色？"
        ]
        
        for query in test_queries:
            print(f"\n問題：{query}")
            response = rag_service.ask(query)
            print(f"回答：{response.answer}")
            print(f"信心度：{response.confidence_score:.2f}")
            print(f"來源數量：{len(response.sources)}")
        
    except Exception as e:
        print(f"測試失敗：{e}")
        import traceback
        traceback.print_exc()