#!/usr/bin/env python3
"""
Google Maps API 資料撷取程式 - 最終整合版本
自動為福井縣景點撷取 Google Maps 的詳細資訊
包含完整的安全控制、重複檢查、進度恢復功能
"""

import json
import time
import requests
import os
import sys
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime
import subprocess

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_maps_fetcher.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class APIConfig:
    """API 配置類別"""
    api_key: str
    max_daily_calls: int = 400
    batch_size: int = 25
    request_delay: float = 1.2
    retry_count: int = 3
    timeout: int = 10

@dataclass
class APIUsageStats:
    """API 使用量統計"""
    find_place_calls: int = 0
    place_details_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    skipped_duplicates: int = 0
    start_time: str = ""
    
    @property
    def total_calls(self) -> int:
        return self.find_place_calls + self.place_details_calls
    
    def save_stats(self, filename: str = "api_usage_stats.json") -> None:
        """保存使用量統計"""
        stats_dict = asdict(self)
        stats_dict['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats_dict, f, ensure_ascii=False, indent=2)

@dataclass
class LocationInfo:
    """景點基本資訊"""
    city: str
    location: str
    latitude: float
    longitude: float
    
    def get_unique_key(self) -> str:
        """獲取景點的唯一識別鍵"""
        return f"{self.city}_{self.location}_{self.latitude:.6f}_{self.longitude:.6f}"

@dataclass
class GooglePlaceDetails:
    """Google Places API 回傳的詳細資訊"""
    place_id: str
    name: str
    formatted_address: str
    phone_number: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    opening_hours: Optional[Dict[str, Any]] = None
    photos: Optional[List[str]] = None
    reviews: Optional[List[Dict[str, Any]]] = None
    business_status: Optional[str] = None
    types: Optional[List[str]] = None

class SafetyChecker:
    """安全檢查器"""
    
    @staticmethod
    def check_api_key(api_key: str) -> bool:
        """檢查 API 金鑰是否有效"""
        if not api_key:
            return False
            
        # 測試一個簡單的 Find Place 請求
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            'input': '養浩館庭園 福井市',
            'inputtype': 'textquery',
            'fields': 'place_id,name',
            'key': api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                logging.info("✅ API 金鑰驗證成功")
                return True
            elif data.get('status') == 'REQUEST_DENIED':
                logging.error("❌ API 金鑰無效或未啟用 Places API")
                return False
            elif data.get('status') == 'OVER_QUERY_LIMIT':
                logging.error("⚠️ API 查詢限制已達上限")
                return False
            else:
                logging.error(f"⚠️ API 回應異常: {data.get('status')}")
                return False
                
        except requests.RequestException as e:
            logging.error(f"❌ API 測試失敗: {e}")
            return False
    
    @staticmethod
    def estimate_cost(location_count: int) -> bool:
        """估算成本並檢查是否安全"""
        estimated_calls = location_count * 2
        usage_rate = estimated_calls / 17000 * 100
        
        logging.info(f"📊 成本估算:")
        logging.info(f"景點數量: {location_count}")
        logging.info(f"預估 API 調用: {estimated_calls}")
        logging.info(f"免費額度使用率: {usage_rate:.1f}%")
        
        if estimated_calls > 17000:
            logging.warning("⚠️ 警告：可能超過免費額度！")
            return False
        elif estimated_calls > 10000:
            logging.warning("⚠️ 注意：使用率較高，建議監控")
        else:
            logging.info("✅ 在安全範圍內")
        
        return True

class DuplicateChecker:
    """重複檢查器"""
    
    def __init__(self):
        self.processed_keys: Set[str] = set()
        self.load_existing_data()
    
    def load_existing_data(self) -> None:
        """載入已存在的資料來建立重複檢查清單"""
        # 檢查各種可能的輸出檔案
        output_files = [
            "../output/fukui_enhanced_locations.json",
            "../output/fukui_enhanced_locations_full.json"
        ]
        
        # 檢查進度檔案
        progress_files = list(Path(".").glob("fukui_enhanced_progress_*.json"))
        
        all_files = output_files + [str(f) for f in progress_files]
        
        for file_path in all_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data:
                        if 'original_data' in item:
                            original = item['original_data']
                            location = LocationInfo(
                                city=original['city'],
                                location=original['location'],
                                latitude=original['latitude'],
                                longitude=original['longitude']
                            )
                            self.processed_keys.add(location.get_unique_key())
                
                except Exception as e:
                    logging.warning(f"無法載入檔案 {file_path}: {e}")
        
        if self.processed_keys:
            logging.info(f"🔍 發現 {len(self.processed_keys)} 個已處理的景點")
    
    def is_duplicate(self, location: LocationInfo) -> bool:
        """檢查是否為重複景點"""
        return location.get_unique_key() in self.processed_keys
    
    def mark_processed(self, location: LocationInfo) -> None:
        """標記景點為已處理"""
        self.processed_keys.add(location.get_unique_key())

class GoogleMapsAPIClient:
    """Google Maps API 客戶端 - 完整功能版本"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.places_base_url = "https://maps.googleapis.com/maps/api/place"
        self.session = requests.Session()
        self.usage_stats = APIUsageStats(start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
    def check_daily_limit(self) -> bool:
        """檢查是否超過每日使用限制"""
        if self.usage_stats.total_calls >= self.config.max_daily_calls:
            logging.error(f"已達到每日API調用限制 ({self.config.max_daily_calls})")
            return False
        return True
        
    def find_place(self, query: str, location: tuple) -> Optional[str]:
        """使用 Find Place API 找到最匹配的地點"""
        if not self.check_daily_limit():
            return None
            
        url = f"{self.places_base_url}/findplacefromtext/json"
        
        params = {
            'input': query,
            'inputtype': 'textquery',
            'fields': 'place_id,name,geometry',
            'locationbias': f'circle:5000@{location[0]},{location[1]}',
            'language': 'ja',
            'key': self.config.api_key
        }
        
        for attempt in range(self.config.retry_count):
            try:
                self.usage_stats.find_place_calls += 1
                response = self.session.get(url, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                
                if data.get('status') == 'OK' and data.get('candidates'):
                    self.usage_stats.successful_calls += 1
                    return data['candidates'][0]['place_id']
                elif data.get('status') == 'ZERO_RESULTS':
                    logging.warning(f"找不到地點: {query}")
                    return None
                elif data.get('status') == 'OVER_QUERY_LIMIT':
                    logging.error("API 查詢限制已達上限")
                    return None
                else:
                    logging.warning(f"Find Place API 失敗: {data.get('status')}, 重試 {attempt + 1}/{self.config.retry_count}")
                    if attempt < self.config.retry_count - 1:
                        time.sleep(2 ** attempt)
                        
            except requests.RequestException as e:
                self.usage_stats.failed_calls += 1
                logging.error(f"Find Place API 請求失敗 (嘗試 {attempt + 1}): {e}")
                if attempt < self.config.retry_count - 1:
                    time.sleep(2 ** attempt)
                    
        return None
    
    def get_place_details(self, place_id: str) -> Optional[GooglePlaceDetails]:
        """獲取地點詳細資訊"""
        if not self.check_daily_limit():
            return None
            
        url = f"{self.places_base_url}/details/json"
        
        fields = [
            'place_id', 'name', 'formatted_address', 'formatted_phone_number',
            'website', 'rating', 'user_ratings_total', 'price_level',
            'opening_hours', 'photos', 'reviews', 'business_status', 'types'
        ]
        
        params = {
            'place_id': place_id,
            'fields': ','.join(fields),
            'language': 'ja',
            'key': self.config.api_key
        }
        
        for attempt in range(self.config.retry_count):
            try:
                self.usage_stats.place_details_calls += 1
                response = self.session.get(url, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                
                if data.get('status') == 'OK':
                    result = data['result']
                    self.usage_stats.successful_calls += 1
                    
                    # 處理營業時間
                    opening_hours = None
                    if 'opening_hours' in result:
                        opening_hours = {
                            'open_now': result['opening_hours'].get('open_now'),
                            'weekday_text': result['opening_hours'].get('weekday_text', [])
                        }
                    
                    # 處理照片 URL
                    photos = None
                    if 'photos' in result:
                        photos = []
                        for photo in result['photos'][:5]:
                            photo_url = f"{self.places_base_url}/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={self.config.api_key}"
                            photos.append(photo_url)
                    
                    # 處理評論
                    reviews = None
                    if 'reviews' in result:
                        reviews = []
                        for review in result['reviews'][:3]:
                            reviews.append({
                                'author_name': review.get('author_name'),
                                'rating': review.get('rating'),
                                'text': review.get('text'),
                                'time': review.get('time')
                            })
                    
                    return GooglePlaceDetails(
                        place_id=result.get('place_id', ''),
                        name=result.get('name', ''),
                        formatted_address=result.get('formatted_address', ''),
                        phone_number=result.get('formatted_phone_number'),
                        website=result.get('website'),
                        rating=result.get('rating'),
                        user_ratings_total=result.get('user_ratings_total'),
                        price_level=result.get('price_level'),
                        opening_hours=opening_hours,
                        photos=photos,
                        reviews=reviews,
                        business_status=result.get('business_status'),
                        types=result.get('types', [])
                    )
                elif data.get('status') == 'OVER_QUERY_LIMIT':
                    logging.error("API 查詢限制已達上限")
                    return None
                else:
                    logging.warning(f"Place Details API 失敗: {data.get('status')}, 重試 {attempt + 1}/{self.config.retry_count}")
                    if attempt < self.config.retry_count - 1:
                        time.sleep(2 ** attempt)
                        
            except requests.RequestException as e:
                self.usage_stats.failed_calls += 1
                logging.error(f"Place Details API 請求失敗 (嘗試 {attempt + 1}): {e}")
                if attempt < self.config.retry_count - 1:
                    time.sleep(2 ** attempt)
                    
        return None

class FukuiLocationEnhancer:
    """福井景點資料增強器 - 最終完整版本"""
    
    def __init__(self, config: APIConfig):
        self.api_client = GoogleMapsAPIClient(config)
        self.duplicate_checker = DuplicateChecker()
        self.enhanced_data: List[Dict[str, Any]] = []
        self.config = config
        
    def load_fukui_locations(self, file_path: str) -> List[LocationInfo]:
        """載入福井景點資料"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            locations = []
            for item in data:
                locations.append(LocationInfo(
                    city=item['city'],
                    location=item['location'],
                    latitude=item['coordinates']['latitude'],
                    longitude=item['coordinates']['longitude']
                ))
            
            logging.info(f"成功載入 {len(locations)} 個景點")
            return locations
            
        except Exception as e:
            logging.error(f"載入檔案失敗: {e}")
            return []
    
    def enhance_location_data(self, locations: List[LocationInfo]) -> None:
        """增強景點資料（含重複檢查）"""
        total = len(locations)
        processed_count = 0
        
        # 過濾掉重複的景點
        unique_locations = []
        for location in locations:
            if self.duplicate_checker.is_duplicate(location):
                self.api_client.usage_stats.skipped_duplicates += 1
                logging.info(f"跳過重複景點: {location.city} - {location.location}")
            else:
                unique_locations.append(location)
        
        if not unique_locations:
            logging.info("所有景點都已處理過，無需重複處理")
            return
        
        remaining_calls = len(unique_locations) * 2
        logging.info(f"預計處理 {len(unique_locations)} 個新景點，需要 {remaining_calls} 次 API 調用")
        
        for i, location in enumerate(unique_locations, 1):
            logging.info(f"處理中 ({i}/{len(unique_locations)}): {location.city} - {location.location}")
            
            # 建立搜尋查詢
            search_query = f"{location.location} {location.city} 福井"
            location_coords = (location.latitude, location.longitude)
            
            # 尋找地點
            place_id = self.api_client.find_place(search_query, location_coords)
            
            enhanced_item = {
                'original_data': asdict(location),
                'google_maps_data': None,
                'search_query': search_query,
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'processing_index': i - 1,
                'unique_key': location.get_unique_key()
            }
            
            if place_id:
                # 獲取詳細資訊
                place_details = self.api_client.get_place_details(place_id)
                if place_details:
                    enhanced_item['google_maps_data'] = asdict(place_details)
                    logging.info(f"成功獲取資料: {place_details.name}")
                else:
                    logging.warning(f"無法獲取詳細資料: {location.location}")
            else:
                logging.warning(f"找不到對應的 Google Places: {location.location}")
            
            self.enhanced_data.append(enhanced_item)
            self.duplicate_checker.mark_processed(location)
            processed_count += 1
            
            # 顯示使用量統計
            stats = self.api_client.usage_stats
            logging.info(f"API 使用量 - 總計: {stats.total_calls}, 成功: {stats.successful_calls}, 失敗: {stats.failed_calls}, 跳過: {stats.skipped_duplicates}")
            
            # API 限流
            time.sleep(self.config.request_delay)
            
            # 定期保存進度
            if i % self.config.batch_size == 0:
                self.save_progress(f"fukui_enhanced_progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                self.api_client.usage_stats.save_stats(f"api_stats_{i}.json")
                
            # 檢查是否達到每日限制
            if not self.api_client.check_daily_limit():
                logging.info(f"已達到每日限制，停止處理。已處理 {i} 個景點")
                break
    
    def save_progress(self, filename: str) -> None:
        """保存進度"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.enhanced_data, f, ensure_ascii=False, indent=2)
            logging.info(f"進度已保存到: {filename}")
        except Exception as e:
            logging.error(f"保存進度失敗: {e}")
    
    def save_final_results(self, output_path: str) -> None:
        """保存最終結果"""
        try:
            # 確保輸出目錄存在
            Path(output_path).parent.mkdir(exist_ok=True)
            
            # 保存完整資料
            full_output_path = output_path.replace('.json', '_full.json')
            with open(full_output_path, 'w', encoding='utf-8') as f:
                json.dump(self.enhanced_data, f, ensure_ascii=False, indent=2)
            
            # 保存簡化版本（只包含有 Google 資料的景點）
            successful_data = [
                item for item in self.enhanced_data 
                if item['google_maps_data'] is not None
            ]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(successful_data, f, ensure_ascii=False, indent=2)
            
            # 保存最終使用量統計
            self.api_client.usage_stats.save_stats("final_api_usage_stats.json")
            
            stats = self.api_client.usage_stats
            logging.info("="*50)
            logging.info("📈 最終統計報告:")
            logging.info(f"完整資料已保存到: {full_output_path}")
            logging.info(f"成功資料已保存到: {output_path}")
            logging.info(f"新處理景點: {len(self.enhanced_data)}")
            logging.info(f"成功獲取: {len(successful_data)} 個景點的 Google 資料")
            logging.info(f"跳過重複: {stats.skipped_duplicates}")
            logging.info(f"API 總調用: {stats.total_calls}")
            logging.info(f"成功率: {stats.successful_calls/max(stats.total_calls,1)*100:.1f}%")
            logging.info("="*50)
            
        except Exception as e:
            logging.error(f"保存最終結果失敗: {e}")

def load_config() -> APIConfig:
    """載入配置設定"""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    if not api_key:
        logging.error("\n❌ 未設定 Google Maps API 金鑰")
        logging.error("請選擇以下方式之一：")
        logging.error("1. 設定環境變數: export GOOGLE_MAPS_API_KEY=你的API金鑰")
        logging.error("2. 執行測試: python3 ../test_api.py")
        raise ValueError("必須提供 Google Maps API 金鑰")
    
    return APIConfig(
        api_key=api_key,
        max_daily_calls=int(os.getenv("MAX_DAILY_API_CALLS", "400")),
        batch_size=int(os.getenv("BATCH_SIZE", "25")),
        request_delay=float(os.getenv("REQUEST_DELAY", "1.2")),
        retry_count=int(os.getenv("RETRY_COUNT", "3")),
        timeout=int(os.getenv("TIMEOUT", "10"))
    )

def print_usage_info():
    """印出使用量資訊"""
    print("\n=== Google Maps API 免費額度 ===")
    print("Find Place API: 17,000 次/月")
    print("Place Details API: 17,000 次/月")
    print("Places Photos API: 17,000 次/月")
    print("\n您的景點數量: 249")
    print("預估 API 調用次數: 498 (249 × 2)")
    print("佔用免費額度比例: 2.9%")
    print("=== 安全範圍內 ===\n")

def pre_flight_checks(config: APIConfig, input_file: str) -> tuple[bool, int]:
    """執行起飛前檢查"""
    logging.info("🛫 執行起飛前安全檢查...")
    
    # 檢查資料檔案
    if not Path(input_file).exists():
        logging.error(f"❌ 找不到資料檔案: {input_file}")
        return False, 0
    
    # 載入資料並計算數量
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        location_count = len(data)
        logging.info(f"✅ 資料檔案檢查通過，包含 {location_count} 個景點")
    except Exception as e:
        logging.error(f"❌ 資料檔案讀取失敗: {e}")
        return False, 0
    
    # 測試 API 金鑰
    if not SafetyChecker.check_api_key(config.api_key):
        return False, 0
    
    # 估算成本
    if not SafetyChecker.estimate_cost(location_count):
        choice = input("\n⚠️ 是否仍要繼續執行？(y/n): ").strip().lower()
        if choice != 'y':
            logging.info("👋 用戶取消執行")
            return False, 0
    
    logging.info("✅ 所有安全檢查通過")
    return True, location_count

def main():
    """主程式"""
    logging.info("🗾 福井景點資料增強工具 - 最終整合版本")
    logging.info("="*60)
    
    try:
        # 載入配置
        config = load_config()
        masked_key = config.api_key[:10] + "..." + config.api_key[-4:] if len(config.api_key) > 14 else "***"
        logging.info(f"🔑 使用 API 金鑰: {masked_key}")
        
    except ValueError as e:
        logging.error(f"配置錯誤: {e}")
        return
    
    # 設定檔案路徑
    input_file = "../data/fukui_location.json"
    output_file = "../output/fukui_enhanced_locations.json"
    
    # 顯示使用量資訊
    print_usage_info()
    
    # 執行起飛前檢查
    checks_passed, location_count = pre_flight_checks(config, input_file)
    if not checks_passed:
        return
    
    # 最終確認
    logging.info("\n" + "="*60)
    choice = input("🚀 準備開始執行，是否繼續？(y/n): ").strip().lower()
    
    if choice != 'y':
        logging.info("👋 程式結束")
        return
    
    # 確保輸出目錄存在
    Path("../output").mkdir(exist_ok=True)
    
    # 建立增強器
    enhancer = FukuiLocationEnhancer(config)
    
    # 載入原始資料
    locations = enhancer.load_fukui_locations(input_file)
    if not locations:
        logging.error("無法載入景點資料，程式結束")
        return
    
    # 增強資料
    logging.info("🚀 開始增強景點資料...")
    try:
        enhancer.enhance_location_data(locations)
    except KeyboardInterrupt:
        logging.info("\n⏸️ 程式被用戶中斷")
        logging.info("📁 進度已保存，可稍後繼續執行")
    except Exception as e:
        logging.error(f"❌ 執行錯誤: {e}")
    
    # 保存結果
    enhancer.save_final_results(output_file)
    
    logging.info("🎉 程式執行完成！")

if __name__ == "__main__":
    main() 