#!/usr/bin/env python3
"""
福井神社導航系統啟動腳本
檢查環境並啟動完整的 Web 服務
"""

import sys
import os
import logging
from pathlib import Path
import subprocess

# 添加專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_logging():
    """設定日誌"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def check_environment():
    """檢查環境配置"""
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 檢查環境配置...")
    
    # 檢查 Python 版本
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        logger.error("Python 版本需要 3.8 或更高")
        return False
    
    logger.info(f"✅ Python 版本: {python_version.major}.{python_version.minor}")
    
    # 檢查必要模組
    required_modules = [
        'fastapi', 'uvicorn', 'chromadb', 'openai', 
        'pydantic', 'geohash', 'numpy'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module} 已安裝")
        except ImportError:
            missing_modules.append(module)
            logger.error(f"❌ {module} 未安裝")
    
    if missing_modules:
        logger.error(f"請安裝缺少的模組: pip install {' '.join(missing_modules)}")
        return False
    
    # 檢查 OpenAI API Key
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning("⚠️  未設定 OPENAI_API_KEY 環境變數")
        logger.warning("   AI 問答功能將無法使用")
    else:
        logger.info("✅ OPENAI_API_KEY 已設定")
    
    # 檢查向量資料庫
    vector_db_path = project_root / "data" / "vector_db"
    if not vector_db_path.exists():
        logger.warning(f"⚠️  向量資料庫不存在: {vector_db_path}")
        logger.warning("   請先執行 tools/setup_vector_db.py 初始化資料庫")
        return False
    else:
        logger.info(f"✅ 向量資料庫存在: {vector_db_path}")
    
    # 檢查靜態檔案
    static_path = project_root / "src" / "main" / "resources" / "static"
    if not static_path.exists():
        logger.error(f"❌ 靜態檔案目錄不存在: {static_path}")
        return False
    
    required_files = ["index.html", "app.js", "style.css"]
    for file in required_files:
        file_path = static_path / file
        if not file_path.exists():
            logger.error(f"❌ 缺少檔案: {file_path}")
            return False
        else:
            logger.info(f"✅ 檔案存在: {file}")
    
    return True


def start_server():
    """啟動伺服器"""
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 啟動福井神社導航系統...")
    
    # 設定環境變數
    os.environ.setdefault('PYTHONPATH', str(project_root))
    
    try:
        # 啟動 FastAPI 伺服器
        cmd = [
            sys.executable, "-m", "uvicorn",
            "src.main.python.app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ]
        
        logger.info("伺服器啟動指令:")
        logger.info(f"  {' '.join(cmd)}")
        logger.info("")
        logger.info("🌐 服務連結:")
        logger.info("  - API 端點: http://localhost:8000")
        logger.info("  - API 文檔: http://localhost:8000/docs")
        logger.info("  - Web 介面: http://localhost:8000/web")
        logger.info("  - 健康檢查: http://localhost:8000/health")
        logger.info("")
        logger.info("按 Ctrl+C 停止伺服器")
        logger.info("=" * 50)
        
        # 執行伺服器
        subprocess.run(cmd, cwd=project_root)
        
    except KeyboardInterrupt:
        logger.info("\n🛑 伺服器已停止")
    except Exception as e:
        logger.error(f"❌ 啟動伺服器失敗: {e}")
        return False
    
    return True


def main():
    """主要執行函數"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("🏮 福井神社導航系統啟動器")
    logger.info("=" * 50)
    
    # 檢查環境
    if not check_environment():
        logger.error("❌ 環境檢查失敗，無法啟動系統")
        return False
    
    logger.info("✅ 環境檢查通過")
    logger.info("")
    
    # 啟動伺服器
    return start_server()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"啟動失敗: {e}")
        sys.exit(1)