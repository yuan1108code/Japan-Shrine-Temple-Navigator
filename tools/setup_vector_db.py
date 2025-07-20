#!/usr/bin/env python3
"""
向量資料庫初始化工具
讀取現有的地點資料並建立向量索引
"""

import sys
import json
import logging
from pathlib import Path

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main.python.services.vector_db import VectorDatabase, VectorDBConfig
from src.main.python.core.embeddings import EmbeddingManager


def setup_logging():
    """設定日誌"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vector_db_setup.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def load_location_data(data_path: str) -> list:
    """載入地點資料"""
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'locations' in data:
            return data['locations']
        else:
            logging.error(f"Unexpected data format in {data_path}")
            return []
            
    except Exception as e:
        logging.error(f"Error loading data from {data_path}: {e}")
        return []


def validate_location_data(locations: list) -> list:
    """驗證和清理地點資料"""
    valid_locations = []
    
    for i, location in enumerate(locations):
        try:
            # 檢查必要欄位
            if not location.get('id'):
                logging.warning(f"Location {i} missing ID, skipping")
                continue
            
            if not location.get('searchable_text'):
                # 如果沒有 searchable_text，嘗試從其他欄位構建
                text_parts = []
                
                if location.get('primary_name'):
                    text_parts.append(location['primary_name'])
                
                if location.get('description'):
                    text_parts.append(location['description'])
                
                if location.get('all_tags'):
                    tags = location['all_tags']
                    if isinstance(tags, list):
                        text_parts.extend(tags)
                    elif isinstance(tags, str):
                        text_parts.append(tags)
                
                if text_parts:
                    location['searchable_text'] = ' '.join(str(part) for part in text_parts)
                else:
                    logging.warning(f"Location {location.get('id')} has no searchable content, skipping")
                    continue
            
            # 確保有基本的元資料
            if not location.get('category'):
                location['category'] = '未分類'
            
            if not location.get('all_tags'):
                location['all_tags'] = []
            
            if not location.get('coordinates'):
                location['coordinates'] = {}
            
            valid_locations.append(location)
            
        except Exception as e:
            logging.warning(f"Error validating location {i}: {e}")
            continue
    
    logging.info(f"Validated {len(valid_locations)} out of {len(locations)} locations")
    return valid_locations


def main():
    """主要執行函數"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 檢查 OPENAI_API_KEY
    import os
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY environment variable not set")
        return False
    
    try:
        # 設定路徑
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "output"
        
        # 尋找最新的統一資料檔案
        unified_data_files = [
            "unified_locations.json",
            "fukui_enhanced_locations_full.json", 
            "fukui_enhanced_locations.json"
        ]
        
        data_file = None
        for filename in unified_data_files:
            file_path = data_dir / filename
            if file_path.exists():
                data_file = file_path
                break
        
        if not data_file:
            logger.error(f"No location data file found in {data_dir}")
            logger.info(f"Looking for: {unified_data_files}")
            return False
        
        logger.info(f"Using data file: {data_file}")
        
        # 載入地點資料
        locations = load_location_data(str(data_file))
        if not locations:
            logger.error("No locations loaded")
            return False
        
        logger.info(f"Loaded {len(locations)} locations")
        
        # 驗證資料
        valid_locations = validate_location_data(locations)
        if not valid_locations:
            logger.error("No valid locations found")
            return False
        
        # 創建向量資料庫
        config = VectorDBConfig(
            db_path=str(project_root / "data" / "vector_db"),
            collection_name="fukui_locations",
            max_results=20,
            similarity_threshold=0.6
        )
        
        logger.info(f"Initializing vector database at {config.db_path}")
        vector_db = VectorDatabase(config)
        
        # 重置資料庫（如果已存在）
        logger.info("Resetting existing database...")
        vector_db.reset_database()
        
        # 添加地點資料
        logger.info(f"Adding {len(valid_locations)} locations to vector database...")
        success = vector_db.add_locations(valid_locations)
        
        if success:
            # 獲取統計資訊
            stats = vector_db.get_collection_stats()
            logger.info(f"Vector database setup completed successfully!")
            logger.info(f"Statistics: {stats}")
            
            # 測試搜尋功能
            logger.info("Testing search functionality...")
            test_queries = ["神社", "歷史", "美食", "景點"]
            
            for query in test_queries:
                results = vector_db.search(query, max_results=3)
                logger.info(f"Query '{query}': Found {len(results)} results")
                for i, result in enumerate(results):
                    logger.info(f"  {i+1}. {result.metadata.get('name', 'Unknown')} (score: {result.similarity_score:.3f})")
            
            # 匯出設定檔
            config_file = project_root / "data" / "vector_db_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"Configuration saved to {config_file}")
            return True
            
        else:
            logger.error("Failed to add locations to vector database")
            return False
            
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)