"""
福井神社導航 FastAPI 應用程式
提供 RAG 問答、地點搜尋等 API 服務
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .api.rag_api import RAGAPIHandler, RAGConfig
from .services.vector_db import VectorDatabase, VectorDBConfig


# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic 模型
class QuestionRequest(BaseModel):
    """問題請求模型"""
    query: str = Field(..., description="使用者問題", min_length=1, max_length=500)
    max_results: Optional[int] = Field(5, description="最大搜尋結果數", ge=1, le=20)


class LocationQuestionRequest(BaseModel):
    """地點問題請求模型"""
    location_id: str = Field(..., description="地點 ID")
    question: str = Field(..., description="關於地點的問題", min_length=1, max_length=300)


class RecommendationRequest(BaseModel):
    """推薦請求模型"""
    category: Optional[str] = Field(None, description="地點類別")
    interests: Optional[List[str]] = Field(None, description="興趣標籤")
    location_type: Optional[str] = Field(None, description="地點類型")


class SearchRequest(BaseModel):
    """搜尋請求模型"""
    query: str = Field(..., description="搜尋關鍵詞", min_length=1, max_length=200)
    max_results: Optional[int] = Field(10, description="最大結果數", ge=1, le=50)
    category: Optional[str] = Field(None, description="過濾類別")


# 全域變數
rag_handler: Optional[RAGAPIHandler] = None
vector_db: Optional[VectorDatabase] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global rag_handler, vector_db
    
    # 啟動時初始化
    logger.info("Initializing Japan Shrine Navigator API...")
    
    try:
        # 設定路徑
        project_root = Path(__file__).parent.parent.parent.parent
        vector_db_path = project_root / "data" / "vector_db"
        
        # 檢查向量資料庫是否存在
        if not vector_db_path.exists():
            logger.error(f"Vector database not found at {vector_db_path}")
            logger.info("Please run tools/setup_vector_db.py first")
            raise RuntimeError("Vector database not initialized")
        
        # 檢查 OpenAI API Key
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("OPENAI_API_KEY environment variable not set")
            raise RuntimeError("OpenAI API key not configured")
        
        # 初始化向量資料庫
        db_config = VectorDBConfig(db_path=str(vector_db_path))
        vector_db = VectorDatabase(db_config)
        
        # 初始化 RAG 服務
        rag_config = RAGConfig(
            model_name="gpt-3.5-turbo",
            max_search_results=5,
            similarity_threshold=0.6,
            temperature=0.7
        )
        rag_handler = RAGAPIHandler(str(vector_db_path), rag_config)
        
        # 獲取資料庫統計
        stats = vector_db.get_collection_stats()
        logger.info(f"Vector database loaded: {stats}")
        logger.info("API initialization completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize API: {e}")
        raise
    
    # 關閉時清理
    logger.info("Shutting down Japan Shrine Navigator API...")


# 創建 FastAPI 應用
app = FastAPI(
    title="福井神社導航 API",
    description="提供福井縣神社和景點的智慧問答與搜尋服務",
    version="1.0.0",
    lifespan=lifespan
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境中應該限制具體域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 依賴注入
def get_rag_handler() -> RAGAPIHandler:
    """獲取 RAG 處理器"""
    if rag_handler is None:
        raise HTTPException(status_code=503, detail="RAG service not initialized")
    return rag_handler


def get_vector_db() -> VectorDatabase:
    """獲取向量資料庫"""
    if vector_db is None:
        raise HTTPException(status_code=503, detail="Vector database not initialized")
    return vector_db


# API 端點
@app.get("/")
async def root():
    """根端點"""
    return {
        "message": "福井神社導航 API",
        "version": "1.0.0",
        "status": "運行中"
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    try:
        stats = rag_handler.get_service_stats() if rag_handler else {}
        return {
            "status": "healthy",
            "timestamp": "2025-07-20",
            "database_ready": vector_db is not None,
            "rag_ready": rag_handler is not None,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.post("/ask")
async def ask_question(
    request: QuestionRequest,
    handler: RAGAPIHandler = Depends(get_rag_handler)
):
    """智慧問答端點"""
    try:
        response = await handler.handle_question(request.query)
        return {
            "success": True,
            "data": response
        }
    except Exception as e:
        logger.error(f"Error in ask endpoint: {e}")
        raise HTTPException(status_code=500, detail="處理問題時發生錯誤")


@app.post("/ask/location")
async def ask_about_location(
    request: LocationQuestionRequest,
    handler: RAGAPIHandler = Depends(get_rag_handler)
):
    """地點相關問答端點"""
    try:
        response = await handler.handle_location_question(
            request.location_id, 
            request.question
        )
        return {
            "success": True,
            "data": response
        }
    except Exception as e:
        logger.error(f"Error in location ask endpoint: {e}")
        raise HTTPException(status_code=500, detail="處理地點問題時發生錯誤")


@app.post("/recommendations")
async def get_recommendations(
    request: RecommendationRequest,
    handler: RAGAPIHandler = Depends(get_rag_handler)
):
    """推薦端點"""
    try:
        preferences = {
            "category": request.category,
            "interests": request.interests,
            "location_type": request.location_type
        }
        response = await handler.handle_recommendations(preferences)
        return {
            "success": True,
            "data": response
        }
    except Exception as e:
        logger.error(f"Error in recommendations endpoint: {e}")
        raise HTTPException(status_code=500, detail="生成推薦時發生錯誤")


@app.post("/search")
async def search_locations(
    request: SearchRequest,
    db: VectorDatabase = Depends(get_vector_db)
):
    """地點搜尋端點"""
    try:
        # 構建過濾條件
        filters = {}
        if request.category:
            filters["category"] = request.category
        
        # 執行搜尋
        results = db.search(
            query=request.query,
            max_results=request.max_results,
            filters=filters if filters else None
        )
        
        # 格式化結果
        formatted_results = [result.to_dict() for result in results]
        
        return {
            "success": True,
            "data": {
                "query": request.query,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail="搜尋時發生錯誤")


@app.get("/locations/{location_id}")
async def get_location_details(
    location_id: str,
    db: VectorDatabase = Depends(get_vector_db)
):
    """獲取地點詳細資訊"""
    try:
        from .services.vector_db import VectorSearchService
        search_service = VectorSearchService(db)
        
        context = search_service.get_location_context(location_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="地點不存在")
        
        return {
            "success": True,
            "data": context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in location details endpoint: {e}")
        raise HTTPException(status_code=500, detail="獲取地點資訊時發生錯誤")


@app.get("/categories")
async def get_categories(db: VectorDatabase = Depends(get_vector_db)):
    """獲取所有地點類別"""
    try:
        stats = db.get_collection_stats()
        categories = stats.get("categories", [])
        
        return {
            "success": True,
            "data": {
                "categories": categories,
                "total_locations": stats.get("total_chunks", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in categories endpoint: {e}")
        raise HTTPException(status_code=500, detail="獲取類別時發生錯誤")


@app.get("/stats")
async def get_service_stats(handler: RAGAPIHandler = Depends(get_rag_handler)):
    """獲取服務統計資訊"""
    try:
        stats = handler.get_service_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error in stats endpoint: {e}")
        raise HTTPException(status_code=500, detail="獲取統計資訊時發生錯誤")


# 錯誤處理
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "success": False,
        "error": "端點不存在",
        "detail": "請檢查 API 路徑是否正確"
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "success": False,
        "error": "伺服器內部錯誤",
        "detail": "請稍後再試或聯繫系統管理員"
    }


if __name__ == "__main__":
    # 開發模式運行
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )