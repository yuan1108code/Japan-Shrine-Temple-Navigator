#!/usr/bin/env python3
"""
RAG API 測試工具
測試向量資料庫和 RAG 問答功能
"""

import sys
import os
import json
import logging
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main.python.services.vector_db import VectorDatabase, VectorDBConfig
from src.main.python.api.rag_api import RAGService, RAGConfig


def setup_logging():
    """設定日誌"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_vector_database():
    """測試向量資料庫"""
    print("🔍 測試向量資料庫...")
    
    try:
        # 初始化向量資料庫
        config = VectorDBConfig(
            db_path=str(project_root / "data" / "vector_db"),
            collection_name="fukui_locations"
        )
        
        vector_db = VectorDatabase(config)
        
        # 獲取統計資訊
        stats = vector_db.get_collection_stats()
        print(f"✅ 向量資料庫連接成功")
        print(f"   - 資料庫路徑: {config.db_path}")
        print(f"   - 集合名稱: {config.collection_name}")
        print(f"   - 總文檔數: {stats.get('total_chunks', 0)}")
        print(f"   - 可用類別: {len(stats.get('categories', []))}")
        
        # 測試搜尋功能
        test_queries = ["神社", "美食", "歷史"]
        
        for query in test_queries:
            results = vector_db.search(query, max_results=3)
            print(f"   - 搜尋 '{query}': 找到 {len(results)} 個結果")
            
            for i, result in enumerate(results[:2]):  # 只顯示前兩個
                print(f"     {i+1}. {result.metadata.get('name', '未知')} (相似度: {result.similarity_score:.3f})")
        
        return vector_db
        
    except Exception as e:
        print(f"❌ 向量資料庫測試失敗: {e}")
        return None


def test_rag_service(vector_db):
    """測試 RAG 服務"""
    print("\n🤖 測試 RAG 問答服務...")
    
    # 檢查 API 金鑰
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 未設定 OPENAI_API_KEY 環境變數")
        print("   請設定後再測試 RAG 功能")
        return False
    
    try:
        # 初始化 RAG 服務
        config = RAGConfig(
            model_name="gpt-3.5-turbo",
            max_search_results=3,
            temperature=0.7,
            max_tokens=300
        )
        
        rag_service = RAGService(vector_db, config)
        print("✅ RAG 服務初始化成功")
        
        # 測試問答
        test_questions = [
            "福井有哪些著名的神社？",
            "請推薦適合家庭旅遊的景點",
            "福井的特色美食有哪些？"
        ]
        
        for question in test_questions:
            print(f"\n   問題: {question}")
            
            try:
                response = rag_service.ask(question)
                
                print(f"   回答: {response.answer[:100]}{'...' if len(response.answer) > 100 else ''}")
                print(f"   信心度: {response.confidence_score:.3f}")
                print(f"   參考來源: {len(response.sources)} 個")
                
                # 顯示主要來源
                if response.sources:
                    main_source = response.sources[0]
                    print(f"   主要來源: {main_source.get('name', '未知地點')}")
                
            except Exception as e:
                print(f"   ❌ 問答失敗: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG 服務測試失敗: {e}")
        return False


def test_specific_location(vector_db):
    """測試特定地點查詢"""
    print("\n📍 測試地點相關查詢...")
    
    try:
        from src.main.python.services.vector_db import VectorSearchService
        search_service = VectorSearchService(vector_db)
        
        # 搜尋一個地點
        results = vector_db.search("神社", max_results=1)
        
        if results:
            location_id = results[0].location_id
            context = search_service.get_location_context(location_id)
            
            if context:
                print(f"✅ 地點查詢成功")
                print(f"   - 地點 ID: {location_id}")
                print(f"   - 地點名稱: {context['metadata'].get('name', '未知')}")
                print(f"   - 地點類別: {context['metadata'].get('category', '未分類')}")
                print(f"   - 文本長度: {len(context['full_text'])} 字元")
                return True
            else:
                print("❌ 無法獲取地點詳細資訊")
                return False
        else:
            print("❌ 找不到測試地點")
            return False
            
    except Exception as e:
        print(f"❌ 地點查詢測試失敗: {e}")
        return False


def generate_test_report():
    """生成測試報告"""
    print("\n📊 生成測試報告...")
    
    report = {
        "test_timestamp": "2025-07-20",
        "test_results": {},
        "system_info": {
            "python_version": sys.version,
            "project_root": str(project_root),
            "openai_key_set": bool(os.getenv('OPENAI_API_KEY'))
        }
    }
    
    try:
        # 向量資料庫測試
        vector_db = test_vector_database()
        report["test_results"]["vector_database"] = vector_db is not None
        
        if vector_db:
            # RAG 服務測試
            rag_success = test_rag_service(vector_db)
            report["test_results"]["rag_service"] = rag_success
            
            # 地點查詢測試
            location_success = test_specific_location(vector_db)
            report["test_results"]["location_query"] = location_success
        
        # 儲存報告
        report_file = project_root / "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 測試報告已儲存至: {report_file}")
        
        # 顯示摘要
        print("\n📋 測試摘要:")
        total_tests = len(report["test_results"])
        passed_tests = sum(report["test_results"].values())
        
        print(f"   - 總測試數: {total_tests}")
        print(f"   - 通過測試: {passed_tests}")
        print(f"   - 成功率: {passed_tests/total_tests*100:.1f}%")
        
        if passed_tests == total_tests:
            print("🎉 所有測試都通過了！RAG API 已準備就緒。")
        else:
            print("⚠️  部分測試失敗，請檢查配置和環境設定。")
        
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"❌ 生成測試報告失敗: {e}")
        return False


def main():
    """主要執行函數"""
    setup_logging()
    
    print("🚀 開始 RAG API 系統測試")
    print("=" * 50)
    
    success = generate_test_report()
    
    print("=" * 50)
    print("測試完成")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)