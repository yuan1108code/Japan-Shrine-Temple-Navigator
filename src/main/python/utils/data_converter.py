"""
資料轉換工具
將現有的 JSON 格式資料轉換為統一的資料模型
"""

import json
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.base_models import CoordinateInfo, ContactInfo, BusinessHours
from models.shrine_models import ShrineInfo, Deity, Festival, CulturalProperty
from models.location_models import TouristLocation, GoogleMapsData, Photo, Review
from models.unified_models import UnifiedLocation


class ShrineDataConverter:
    """神社資料轉換器"""
    
    @staticmethod
    def convert_shrine_json(shrine_data: Dict[str, Any]) -> ShrineInfo:
        """轉換單個神社資料"""
        
        # 座標資訊
        coordinates = CoordinateInfo(
            latitude=shrine_data.get("lat", 0.0),
            longitude=shrine_data.get("lon", 0.0),
            geohash=shrine_data.get("geohash", "")
        )
        
        # 聯絡資訊（神社通常沒有這些資訊）
        contact = ContactInfo()
        
        # 營業時間
        business_hours = BusinessHours(
            is_24_hours=True,  # 大部分神社24小時開放
            weekday_text=[]
        )
        
        # 祭神資訊
        deities = []
        for deity_data in shrine_data.get("enshrined_deities", []):
            if isinstance(deity_data, dict):
                deity = Deity(
                    name=deity_data.get("name", ""),
                    role=deity_data.get("role", ""),
                    description=deity_data.get("description", "")
                )
                deities.append(deity)
        
        # 祭典資訊
        festivals = []
        for festival_data in shrine_data.get("annual_festivals", []):
            if isinstance(festival_data, dict):
                festival = Festival(
                    name=festival_data.get("name", ""),
                    date=festival_data.get("date", ""),
                    description=festival_data.get("description", ""),
                    is_major=festival_data.get("is_major", False)
                )
                festivals.append(festival)
        
        # 文化財產
        cultural_properties = []
        for cp_name in shrine_data.get("important_cultural_property", []):
            if cp_name:
                cp = CulturalProperty(
                    name=cp_name,
                    category="重要文化財",
                    designation_level="重要文化財"
                )
                cultural_properties.append(cp)
        
        # 創建神社資訊
        shrine = ShrineInfo(
            id=str(uuid.uuid4()),
            name_jp=shrine_data.get("name_jp", ""),
            name_en=shrine_data.get("name_en", ""),
            prefecture=shrine_data.get("prefecture", "福井県"),
            city=shrine_data.get("city", ""),
            address=shrine_data.get("address", ""),
            coordinates=coordinates,
            contact=contact,
            business_hours=business_hours,
            data_source="enhanced_shrines_json",
            
            # 神社特定資訊
            shrine_type=shrine_data.get("type", "神社"),
            romaji=shrine_data.get("romaji", ""),
            founded_year=shrine_data.get("founded_year", ""),
            founder=shrine_data.get("founder", ""),
            historical_events=shrine_data.get("historical_events", []),
            architectural_style=shrine_data.get("architectural_style", ""),
            cultural_properties=cultural_properties,
            unesco_heritage=shrine_data.get("unesco", False),
            enshrined_deities=deities,
            prayer_categories=shrine_data.get("prayer_categories", []),
            admission_fee=shrine_data.get("admission_fee", 0.0),
            omamori_types=shrine_data.get("omamori_types", []),
            goshuin_available=shrine_data.get("goshuin", False),
            annual_festivals=festivals,
            ceremonies=shrine_data.get("ceremonies", []),
            nearest_station=shrine_data.get("nearest_station", ""),
            access_time_walk=shrine_data.get("access_time_walk", ""),
            bus_info=shrine_data.get("bus_info", ""),
            parking_info=shrine_data.get("parking", "")
        )
        
        return shrine
    
    @staticmethod
    def convert_shrine_file(file_path: str) -> List[ShrineInfo]:
        """轉換神社 JSON 檔案"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        shrines = []
        for shrine_data in data:
            try:
                shrine = ShrineDataConverter.convert_shrine_json(shrine_data)
                shrines.append(shrine)
            except Exception as e:
                print(f"Error converting shrine data: {e}")
                print(f"Data: {shrine_data}")
                continue
        
        return shrines


class LocationDataConverter:
    """景點資料轉換器"""
    
    @staticmethod
    def convert_location_json(location_data: Dict[str, Any]) -> TouristLocation:
        """轉換單個景點資料"""
        
        original = location_data.get("original_data", {})
        google_data = location_data.get("google_maps_data", {})
        
        # 座標資訊
        lat = original.get("latitude") or google_data.get("geometry", {}).get("location", {}).get("lat", 0.0)
        lon = original.get("longitude") or google_data.get("geometry", {}).get("location", {}).get("lng", 0.0)
        
        coordinates = CoordinateInfo(
            latitude=lat,
            longitude=lon
        )
        
        # 聯絡資訊
        contact = ContactInfo(
            phone=google_data.get("phone_number", ""),
            website=google_data.get("website", "")
        )
        
        # 營業時間
        opening_hours = google_data.get("opening_hours") or {}
        business_hours = BusinessHours(
            is_24_hours=False,
            weekday_text=opening_hours.get("weekday_text", []) if opening_hours else []
        )
        
        # Google Maps 整合資料
        google_integration = None
        if google_data:
            # 照片
            photos = []
            for photo_url in google_data.get("photos", []):
                photo = Photo(url=photo_url)
                photos.append(photo)
            
            # 評論
            reviews = []
            for review_data in google_data.get("reviews", []):
                review = Review(
                    author_name=review_data.get("author_name", ""),
                    rating=review_data.get("rating", 0.0),
                    text=review_data.get("text", ""),
                    time=review_data.get("time", 0)
                )
                reviews.append(review)
            
            google_integration = GoogleMapsData(
                place_id=google_data.get("place_id", ""),
                rating=google_data.get("rating"),
                user_ratings_total=google_data.get("user_ratings_total"),
                price_level=google_data.get("price_level"),
                photos=photos,
                reviews=reviews,
                types=google_data.get("types", []),
                business_status=google_data.get("business_status", "OPERATIONAL")
            )
        
        # 判斷景點類型
        location_type = "tourist_spot"
        if google_data:
            types = google_data.get("types", [])
            if "restaurant" in types or "food" in types:
                location_type = "restaurant"
            elif "shopping" in types or "store" in types:
                location_type = "shopping"
            elif "park" in types:
                location_type = "park"
            elif "museum" in types:
                location_type = "museum"
        
        # 創建景點資訊
        location = TouristLocation(
            id=location_data.get("unique_key", str(uuid.uuid4())),
            name_jp=google_data.get("name", original.get("location", "")),
            prefecture="福井県",
            city=original.get("city", ""),
            address=google_data.get("formatted_address", ""),
            coordinates=coordinates,
            contact=contact,
            business_hours=business_hours,
            data_source="fukui_enhanced_locations",
            
            # 景點特定資訊
            location_type=location_type,
            google_data=google_integration,
            admission_fee=0.0 if google_integration and google_integration.price_level == 0 else None
        )
        
        return location
    
    @staticmethod
    def convert_location_file(file_path: str) -> List[TouristLocation]:
        """轉換景點 JSON 檔案"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        locations = []
        for location_data in data:
            try:
                location = LocationDataConverter.convert_location_json(location_data)
                locations.append(location)
            except Exception as e:
                print(f"Error converting location data: {e}")
                print(f"Data: {location_data}")
                continue
        
        return locations


class UnifiedDataManager:
    """統一資料管理器"""
    
    def __init__(self):
        self.unified_locations: List[UnifiedLocation] = []
    
    def load_from_files(self, shrine_file: str, location_file: str):
        """從檔案載入資料"""
        print(f"Loading shrine data from: {shrine_file}")
        shrines = ShrineDataConverter.convert_shrine_file(shrine_file)
        print(f"Loaded {len(shrines)} shrines")
        
        print(f"Loading location data from: {location_file}")
        locations = LocationDataConverter.convert_location_file(location_file)
        print(f"Loaded {len(locations)} locations")
        
        # 轉換為統一格式
        for shrine in shrines:
            unified = UnifiedLocation.from_shrine(shrine)
            self.unified_locations.append(unified)
        
        for location in locations:
            unified = UnifiedLocation.from_location(location)
            self.unified_locations.append(unified)
        
        print(f"Total unified locations: {len(self.unified_locations)}")
    
    def save_unified_data(self, output_file: str):
        """儲存統一格式資料"""
        data = [location.to_dict() for location in self.unified_locations]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved unified data to: {output_file}")
    
    def get_by_category(self, category: str) -> List[UnifiedLocation]:
        """根據分類獲取地點"""
        return [loc for loc in self.unified_locations if loc.category.value == category]
    
    def get_statistics(self) -> Dict[str, int]:
        """獲取資料統計"""
        stats = {}
        for location in self.unified_locations:
            category = location.category.value
            stats[category] = stats.get(category, 0) + 1
        
        return stats


if __name__ == "__main__":
    # 測試轉換
    manager = UnifiedDataManager()
    
    # 使用相對路徑
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent
    
    shrine_file = project_root / "output" / "enhanced_shrines.json"
    location_file = project_root / "output" / "fukui_enhanced_locations_full.json"
    output_file = project_root / "output" / "unified_locations.json"
    
    manager.load_from_files(str(shrine_file), str(location_file))
    manager.save_unified_data(str(output_file))
    
    print("\nStatistics:")
    for category, count in manager.get_statistics().items():
        print(f"  {category}: {count}")