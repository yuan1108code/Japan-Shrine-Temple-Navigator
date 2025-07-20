"""
向量資料庫服務模組
使用 ChromaDB 提供高效的語義搜尋功能
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    import numpy as np
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from ..core.embeddings import EmbeddingManager, EmbeddingProvider


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜尋結果資料結構"""
    location_id: str
    chunk_index: int
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location_id": self.location_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "similarity_score": self.similarity_score,
            "metadata": self.metadata
        }


@dataclass
class VectorDBConfig:
    """向量資料庫配置"""
    db_path: str = "./data/vector_db"
    collection_name: str = "fukui_locations"
    embedding_dimension: int = 1536
    max_results: int = 10
    similarity_threshold: float = 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "db_path": self.db_path,
            "collection_name": self.collection_name,
            "embedding_dimension": self.embedding_dimension,
            "max_results": self.max_results,
            "similarity_threshold": self.similarity_threshold
        }


class VectorDatabase:
    """向量資料庫管理器"""
    
    def __init__(self, config: Optional[VectorDBConfig] = None, embedding_provider: Optional[EmbeddingProvider] = None):
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        self.config = config or VectorDBConfig()
        self.embedding_manager = EmbeddingManager(embedding_provider)
        
        # 確保資料庫目錄存在
        Path(self.config.db_path).mkdir(parents=True, exist_ok=True)
        
        # 初始化 ChromaDB 客戶端
        self.client = chromadb.PersistentClient(
            path=self.config.db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 獲取或創建集合
        self.collection = self._get_or_create_collection()
        
        logger.info(f"Vector database initialized at {self.config.db_path}")
    
    def _get_or_create_collection(self):
        """獲取或創建向量集合"""
        try:
            # 嘗試獲取現有集合
            collection = self.client.get_collection(name=self.config.collection_name)
            logger.info(f"Found existing collection: {self.config.collection_name}")
        except Exception:
            # 創建新集合
            collection = self.client.create_collection(
                name=self.config.collection_name,
                metadata={"description": "福井地點向量資料"}
            )
            logger.info(f"Created new collection: {self.config.collection_name}")
        
        return collection
    
    def add_locations(self, locations: List[Dict[str, Any]]) -> bool:
        """添加地點資料到向量資料庫"""
        try:
            # 使用嵌入管理器處理地點資料
            chunks = self.embedding_manager.process_locations(locations)
            
            if not chunks:
                logger.warning("No chunks generated from locations")
                return False
            
            # 準備 ChromaDB 資料
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for chunk in chunks:
                # 生成唯一 ID
                chunk_id = f"{chunk['location_id']}_chunk_{chunk['chunk_index']}"
                ids.append(chunk_id)
                
                # 添加嵌入向量
                embeddings.append(chunk['embedding'])
                
                # 添加文本內容
                documents.append(chunk['text'])
                
                # 添加元資料
                metadata = chunk['metadata'].copy()
                metadata.update({
                    'location_id': chunk['location_id'],
                    'chunk_index': chunk['chunk_index']
                })
                metadatas.append(metadata)
            
            # 批量添加到 ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(chunks)} chunks from {len(locations)} locations to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error adding locations to vector database: {e}")
            return False
    
    def search(self, query: str, max_results: Optional[int] = None, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """搜尋向量資料庫"""
        try:
            # 生成查詢的嵌入向量
            query_embedding = self.embedding_manager.process_single_query(query)
            
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            # 設定搜尋參數
            n_results = max_results or self.config.max_results
            
            # 構建 ChromaDB 查詢參數
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results
            }
            
            # 添加過濾條件
            if filters:
                query_params["where"] = filters
            
            # 執行搜尋
            results = self.collection.query(**query_params)
            
            # 轉換結果格式
            search_results = []
            
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # 計算相似度分數 (ChromaDB 返回距離，需要轉換為相似度)
                    distance = results['distances'][0][i]
                    similarity_score = 1.0 / (1.0 + distance)  # 簡單的相似度轉換
                    
                    # 過濾低相似度結果
                    if similarity_score < self.config.similarity_threshold:
                        continue
                    
                    metadata = results['metadatas'][0][i]
                    
                    result = SearchResult(
                        location_id=metadata.get('location_id', ''),
                        chunk_index=metadata.get('chunk_index', 0),
                        content=results['documents'][0][i],
                        similarity_score=similarity_score,
                        metadata=metadata
                    )
                    
                    search_results.append(result)
            
            logger.info(f"Found {len(search_results)} relevant results for query: {query}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []
    
    def search_by_location(self, location_id: str) -> List[SearchResult]:
        """根據地點 ID 搜尋所有相關塊"""
        return self.search(
            query="",  # 空查詢
            filters={"location_id": location_id}
        )
    
    def search_by_category(self, query: str, category: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """根據類別搜尋"""
        return self.search(
            query=query,
            max_results=max_results,
            filters={"category": category}
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """獲取集合統計資訊"""
        try:
            count = self.collection.count()
            
            # 獲取一些樣本資料來分析
            sample_results = self.collection.peek(limit=10)
            
            categories = set()
            if sample_results['metadatas']:
                for metadata in sample_results['metadatas']:
                    if 'category' in metadata:
                        categories.add(metadata['category'])
            
            return {
                "total_chunks": count,
                "collection_name": self.config.collection_name,
                "categories": list(categories),
                "db_path": self.config.db_path
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def update_location(self, location_id: str, updated_data: Dict[str, Any]) -> bool:
        """更新地點資料"""
        try:
            # 刪除舊的塊
            self.delete_location(location_id)
            
            # 添加新的塊
            return self.add_locations([updated_data])
            
        except Exception as e:
            logger.error(f"Error updating location {location_id}: {e}")
            return False
    
    def delete_location(self, location_id: str) -> bool:
        """刪除地點的所有資料"""
        try:
            # 查找所有相關的 ID
            results = self.collection.get(
                where={"location_id": location_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for location {location_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting location {location_id}: {e}")
            return False
    
    def reset_database(self) -> bool:
        """重置整個資料庫"""
        try:
            self.client.delete_collection(name=self.config.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info("Vector database reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
    
    def export_data(self, output_path: str) -> bool:
        """匯出向量資料庫資料"""
        try:
            # 獲取所有資料
            results = self.collection.get(
                include=['embeddings', 'documents', 'metadatas']
            )
            
            export_data = {
                "config": self.config.to_dict(),
                "data": {
                    "ids": results['ids'],
                    "embeddings": results['embeddings'],
                    "documents": results['documents'],
                    "metadatas": results['metadatas']
                },
                "stats": self.get_collection_stats()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported vector database to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False


class VectorSearchService:
    """向量搜尋服務 - 高階介面"""
    
    def __init__(self, vector_db: VectorDatabase):
        self.vector_db = vector_db
    
    def semantic_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """語義搜尋"""
        results = self.vector_db.search(query, max_results)
        return [result.to_dict() for result in results]
    
    def get_location_context(self, location_id: str) -> Dict[str, Any]:
        """獲取地點的完整上下文"""
        chunks = self.vector_db.search_by_location(location_id)
        
        if not chunks:
            return {}
        
        # 合併所有文本塊
        full_text = " ".join([chunk.content for chunk in chunks])
        
        # 獲取元資料
        metadata = chunks[0].metadata if chunks else {}
        
        return {
            "location_id": location_id,
            "full_text": full_text,
            "chunks": [chunk.to_dict() for chunk in chunks],
            "metadata": metadata
        }
    
    def find_similar_locations(self, reference_location_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """找到相似的地點"""
        # 獲取參考地點的資料
        context = self.get_location_context(reference_location_id)
        
        if not context:
            return []
        
        # 使用地點的文本進行搜尋
        results = self.semantic_search(context['full_text'][:500], max_results + 1)
        
        # 過濾掉參考地點本身
        filtered_results = [
            result for result in results 
            if result['location_id'] != reference_location_id
        ]
        
        return filtered_results[:max_results]


# 工具函數
def create_vector_db(config_path: Optional[str] = None) -> VectorDatabase:
    """創建向量資料庫實例"""
    config = VectorDBConfig()
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return VectorDatabase(config)


if __name__ == "__main__":
    # 測試向量資料庫
    logging.basicConfig(level=logging.INFO)
    
    # 創建測試配置
    config = VectorDBConfig(
        db_path="./test_vector_db",
        collection_name="test_locations"
    )
    
    try:
        # 初始化向量資料庫
        vector_db = VectorDatabase(config)
        
        # 測試資料
        test_locations = [
            {
                "id": "test_001",
                "primary_name": "測試神社",
                "category": "神社",
                "searchable_text": "這是一個美麗的神社，擁有悠久的歷史和文化價值。",
                "all_tags": ["神社", "歷史", "文化"],
                "coordinates": {"lat": 36.0, "lng": 136.0}
            }
        ]
        
        # 添加測試資料
        success = vector_db.add_locations(test_locations)
        print(f"Add locations success: {success}")
        
        # 測試搜尋
        results = vector_db.search("歷史悠久的神社")
        print(f"Search results: {len(results)}")
        for result in results:
            print(f"- {result.content} (score: {result.similarity_score:.3f})")
        
        # 獲取統計
        stats = vector_db.get_collection_stats()
        print(f"Collection stats: {stats}")
        
    except Exception as e:
        print(f"Test failed: {e}")