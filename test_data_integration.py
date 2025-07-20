#!/usr/bin/env python3
"""
測試資料整合功能
"""

import json
import sys
import os
from pathlib import Path

# 添加模組路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'main', 'python'))

from models.base_models import CoordinateInfo, ContactInfo, BusinessHours
from models.shrine_models import ShrineInfo, Deity, Festival
from models.location_models import TouristLocation, GoogleMapsData, Photo, Review
from models.unified_models import UnifiedLocation
from utils.data_converter import ShrineDataConverter, LocationDataConverter, UnifiedDataManager


def test_shrine_conversion():
    """測試神社資料轉換"""
    print("Testing shrine data conversion...")
    
    # 讀取神社資料
    shrine_file = "output/enhanced_shrines.json"
    if not os.path.exists(shrine_file):
        print(f"Shrine file not found: {shrine_file}")
        return False
    
    try:
        shrines = ShrineDataConverter.convert_shrine_file(shrine_file)
        print(f"Successfully converted {len(shrines)} shrines")
        
        # 顯示第一個神社的資訊
        if shrines:
            first_shrine = shrines[0]
            print(f"First shrine: {first_shrine.name_jp}")
            print(f"Location: {first_shrine.coordinates.latitude}, {first_shrine.coordinates.longitude}")
            print(f"Tags: {first_shrine.get_all_tags()}")
        
        return True
    except Exception as e:
        print(f"Error converting shrines: {e}")
        return False


def test_location_conversion():
    """測試景點資料轉換"""
    print("\nTesting location data conversion...")
    
    # 讀取景點資料
    location_file = "output/fukui_enhanced_locations_full.json"
    if not os.path.exists(location_file):
        print(f"Location file not found: {location_file}")
        return False
    
    try:
        locations = LocationDataConverter.convert_location_file(location_file)
        print(f"Successfully converted {len(locations)} locations")
        
        # 顯示第一個景點的資訊
        if locations:
            first_location = locations[0]
            print(f"First location: {first_location.name_jp}")
            print(f"Type: {first_location.location_type}")
            print(f"Tags: {first_location.get_all_tags()}")
        
        return True
    except Exception as e:
        print(f"Error converting locations: {e}")
        return False


def test_unified_data():
    """測試統一資料管理"""
    print("\nTesting unified data management...")
    
    try:
        manager = UnifiedDataManager()
        manager.load_from_files(
            "output/enhanced_shrines.json",
            "output/fukui_enhanced_locations_full.json"
        )
        
        # 儲存統一資料
        output_file = "output/unified_locations.json"
        manager.save_unified_data(output_file)
        
        # 顯示統計
        stats = manager.get_statistics()
        print("\nData statistics:")
        for category, count in stats.items():
            print(f"  {category}: {count}")
        
        return True
    except Exception as e:
        print(f"Error in unified data management: {e}")
        return False


def main():
    """主測試函數"""
    print("=" * 50)
    print("Data Integration Test")
    print("=" * 50)
    
    success = True
    
    # 測試神社轉換
    if not test_shrine_conversion():
        success = False
    
    # 測試景點轉換
    if not test_location_conversion():
        success = False
    
    # 測試統一資料管理
    if not test_unified_data():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 50)


if __name__ == "__main__":
    main()