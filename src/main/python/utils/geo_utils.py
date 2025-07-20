"""
地理計算工具
距離計算、Geohash 生成、地理查詢等功能
"""

import math
# import geohash  # Will be installed later
from typing import Tuple, List


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用 Haversine 公式計算兩點間距離（公里）
    
    Args:
        lat1, lon1: 第一個點的經緯度
        lat2, lon2: 第二個點的經緯度
    
    Returns:
        距離（公里）
    """
    R = 6371  # 地球半徑（公里）
    
    # 轉換為弧度
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 計算差值
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine 公式
    a = (math.sin(dlat/2) * math.sin(dlat/2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(dlon/2) * math.sin(dlon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def generate_geohash(lat: float, lon: float, precision: int = 8) -> str:
    """
    生成 Geohash
    
    Args:
        lat: 緯度
        lon: 經度
        precision: 精確度（字符長度）
    
    Returns:
        Geohash 字符串
    """
    # return geohash.encode(lat, lon, precision)
    # Placeholder implementation until geohash is available
    return f"gh_{lat:.6f}_{lon:.6f}"[:precision+3]


def decode_geohash(geohash_str: str) -> Tuple[float, float]:
    """
    解碼 Geohash
    
    Args:
        geohash_str: Geohash 字符串
    
    Returns:
        (緯度, 經度)
    """
    # return geohash.decode(geohash_str)
    # Placeholder implementation
    if geohash_str.startswith("gh_"):
        parts = geohash_str[3:].split("_")
        if len(parts) >= 2:
            return (float(parts[0]), float(parts[1]))
    return (0.0, 0.0)


def is_within_radius(center_lat: float, center_lon: float, 
                    point_lat: float, point_lon: float, 
                    radius_km: float) -> bool:
    """
    判斷點是否在指定半徑內
    
    Args:
        center_lat, center_lon: 中心點經緯度
        point_lat, point_lon: 檢查點經緯度
        radius_km: 半徑（公里）
    
    Returns:
        是否在半徑內
    """
    distance = calculate_distance(center_lat, center_lon, point_lat, point_lon)
    return distance <= radius_km


def get_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    獲取指定半徑的邊界框
    
    Args:
        lat: 中心緯度
        lon: 中心經度
        radius_km: 半徑（公里）
    
    Returns:
        (min_lat, max_lat, min_lon, max_lon)
    """
    # 大約的度數轉換（在日本附近）
    lat_per_km = 1 / 111.0  # 1度緯度約111公里
    lon_per_km = 1 / (111.0 * math.cos(math.radians(lat)))  # 經度隨緯度變化
    
    lat_delta = radius_km * lat_per_km
    lon_delta = radius_km * lon_per_km
    
    return (
        lat - lat_delta,  # min_lat
        lat + lat_delta,  # max_lat
        lon - lon_delta,  # min_lon
        lon + lon_delta   # max_lon
    )


def points_within_radius(center_lat: float, center_lon: float, 
                        points: List[Tuple[float, float]], 
                        radius_km: float) -> List[Tuple[float, float, float]]:
    """
    找出半徑內的所有點
    
    Args:
        center_lat, center_lon: 中心點經緯度
        points: 點列表 [(lat, lon), ...]
        radius_km: 半徑（公里）
    
    Returns:
        [(lat, lon, distance), ...] 在半徑內的點及其距離
    """
    result = []
    
    for lat, lon in points:
        distance = calculate_distance(center_lat, center_lon, lat, lon)
        if distance <= radius_km:
            result.append((lat, lon, distance))
    
    # 按距離排序
    result.sort(key=lambda x: x[2])
    
    return result


def interpolate_points(lat1: float, lon1: float, lat2: float, lon2: float, 
                      num_points: int = 10) -> List[Tuple[float, float]]:
    """
    在兩點間插值生成中間點
    
    Args:
        lat1, lon1: 起點經緯度
        lat2, lon2: 終點經緯度
        num_points: 插值點數量
    
    Returns:
        插值點列表 [(lat, lon), ...]
    """
    points = []
    
    for i in range(num_points + 1):
        ratio = i / num_points
        lat = lat1 + (lat2 - lat1) * ratio
        lon = lon1 + (lon2 - lon1) * ratio
        points.append((lat, lon))
    
    return points


class GeoRegion:
    """地理區域類別"""
    
    def __init__(self, name: str, boundaries: List[Tuple[float, float]]):
        """
        初始化地理區域
        
        Args:
            name: 區域名稱
            boundaries: 邊界點列表 [(lat, lon), ...]
        """
        self.name = name
        self.boundaries = boundaries
    
    def contains_point(self, lat: float, lon: float) -> bool:
        """
        判斷點是否在區域內（簡單的邊界框判斷）
        
        Args:
            lat, lon: 點的經緯度
        
        Returns:
            是否在區域內
        """
        if not self.boundaries:
            return False
        
        lats = [p[0] for p in self.boundaries]
        lons = [p[1] for p in self.boundaries]
        
        return (min(lats) <= lat <= max(lats) and 
                min(lons) <= lon <= max(lons))
    
    def get_center(self) -> Tuple[float, float]:
        """
        獲取區域中心點
        
        Returns:
            (緯度, 經度)
        """
        if not self.boundaries:
            return (0.0, 0.0)
        
        lats = [p[0] for p in self.boundaries]
        lons = [p[1] for p in self.boundaries]
        
        return (sum(lats) / len(lats), sum(lons) / len(lons))


# 預定義的福井縣區域
FUKUI_REGIONS = {
    "福井市": GeoRegion("福井市", [
        (36.0, 136.1),
        (36.1, 136.3),
        (36.2, 136.2),
        (36.05, 136.05)
    ]),
    "あわら市": GeoRegion("あわら市", [
        (36.2, 136.2),
        (36.25, 136.25),
        (36.3, 136.3),
        (36.15, 136.15)
    ])
    # 可以添加更多區域...
}


def get_region_for_point(lat: float, lon: float) -> str:
    """
    根據座標獲取所屬區域
    
    Args:
        lat, lon: 點的經緯度
    
    Returns:
        區域名稱，如果沒找到則返回 "unknown"
    """
    for region_name, region in FUKUI_REGIONS.items():
        if region.contains_point(lat, lon):
            return region_name
    
    return "unknown"