"""
統一資料模型
整合神社和景點資料，提供統一的查詢和搜尋介面
"""

from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import math

from .base_models import LocationBase, TagCategory, CoordinateInfo
from .shrine_models import ShrineInfo
from .location_models import TouristLocation


class LocationCategory(Enum):
    """地點分類"""
    SHRINE = "shrine"
    TEMPLE = "temple"
    TOURIST_SPOT = "tourist_spot"
    RESTAURANT = "restaurant"
    SHOPPING = "shopping"
    NATURE = "nature"
    MUSEUM = "museum"
    PARK = "park"
    OTHER = "other"


@dataclass
class GeoQuery:
    """地理查詢條件"""
    center_lat: float
    center_lon: float
    radius_km: float = 5.0  # 預設半徑5公里
    categories: List[LocationCategory] = field(default_factory=list)
    required_tags: List[TagCategory] = field(default_factory=list)
    exclude_tags: List[TagCategory] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "radius_km": self.radius_km,
            "categories": [cat.value for cat in self.categories],
            "required_tags": [tag.value for tag in self.required_tags],
            "exclude_tags": [tag.value for tag in self.exclude_tags]
        }


@dataclass
class SearchResult:
    """搜尋結果"""
    location: 'UnifiedLocation'
    relevance_score: float
    distance_km: Optional[float] = None
    matched_tags: List[TagCategory] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": self.location.to_dict(),
            "relevance_score": self.relevance_score,
            "distance_km": self.distance_km,
            "matched_tags": [tag.value for tag in self.matched_tags]
        }


@dataclass
class UnifiedLocation:
    """統一的地點模型"""
    base_info: LocationBase
    shrine_info: Optional[ShrineInfo] = None
    location_info: Optional[TouristLocation] = None
    
    def __post_init__(self):
        """初始化後處理"""
        # 確保只有一種類型的資料
        if self.shrine_info and self.location_info:
            raise ValueError("Cannot have both shrine_info and location_info")
        
        # 如果是神社資料，複製基本資訊
        if self.shrine_info:
            self._sync_from_shrine()
        elif self.location_info:
            self._sync_from_location()
    
    def _sync_from_shrine(self):
        """從神社資料同步基本資訊"""
        if not self.shrine_info:
            return
        
        # 如果 base_info 的某些欄位為空，從 shrine_info 複製
        if not self.base_info.name_jp:
            self.base_info.name_jp = self.shrine_info.name_jp
        if not self.base_info.coordinates.latitude:
            self.base_info.coordinates = self.shrine_info.coordinates
    
    def _sync_from_location(self):
        """從景點資料同步基本資訊"""
        if not self.location_info:
            return
        
        # 如果 base_info 的某些欄位為空，從 location_info 複製
        if not self.base_info.name_jp:
            self.base_info.name_jp = self.location_info.name_jp
        if not self.base_info.coordinates.latitude:
            self.base_info.coordinates = self.location_info.coordinates
    
    @property
    def category(self) -> LocationCategory:
        """獲取地點分類"""
        if self.shrine_info:
            if self.shrine_info.shrine_type == "寺":
                return LocationCategory.TEMPLE
            else:
                return LocationCategory.SHRINE
        elif self.location_info:
            type_mapping = {
                "restaurant": LocationCategory.RESTAURANT,
                "shopping": LocationCategory.SHOPPING,
                "park": LocationCategory.PARK,
                "museum": LocationCategory.MUSEUM,
                "tourist_spot": LocationCategory.TOURIST_SPOT
            }
            return type_mapping.get(
                self.location_info.location_type, 
                LocationCategory.OTHER
            )
        else:
            return LocationCategory.OTHER
    
    @property
    def primary_name(self) -> str:
        """獲取主要名稱"""
        if self.shrine_info:
            return self.shrine_info.name_jp
        elif self.location_info:
            return self.location_info.name_jp
        else:
            return self.base_info.name_jp
    
    @property
    def coordinates(self) -> CoordinateInfo:
        """獲取座標資訊"""
        if self.shrine_info:
            return self.shrine_info.coordinates
        elif self.location_info:
            return self.location_info.coordinates
        else:
            return self.base_info.coordinates
    
    @property
    def all_tags(self) -> List[TagCategory]:
        """獲取所有標籤"""
        if self.shrine_info:
            return self.shrine_info.tags
        elif self.location_info:
            return self.location_info.tags
        else:
            return self.base_info.tags
    
    def get_distance_km(self, lat: float, lon: float) -> float:
        """計算與指定座標的距離（公里）"""
        return self._calculate_distance(
            lat, lon,
            self.coordinates.latitude,
            self.coordinates.longitude
        )
    
    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """使用 Haversine 公式計算距離"""
        R = 6371  # 地球半徑（公里）
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def matches_query(self, query: GeoQuery) -> Tuple[bool, float]:
        """檢查是否符合查詢條件"""
        # 檢查距離
        distance = self.get_distance_km(query.center_lat, query.center_lon)
        if distance > query.radius_km:
            return False, 0.0
        
        # 檢查分類
        if query.categories and self.category not in query.categories:
            return False, 0.0
        
        # 檢查必要標籤
        location_tags = set(self.all_tags)
        required_tags = set(query.required_tags)
        exclude_tags = set(query.exclude_tags)
        
        if required_tags and not required_tags.issubset(location_tags):
            return False, 0.0
        
        if exclude_tags and exclude_tags.intersection(location_tags):
            return False, 0.0
        
        # 計算相關性分數（距離越近分數越高）
        max_distance = query.radius_km
        distance_score = (max_distance - distance) / max_distance
        
        # 標籤匹配加分
        tag_bonus = len(required_tags.intersection(location_tags)) * 0.1
        
        relevance_score = min(1.0, distance_score + tag_bonus)
        
        return True, relevance_score
    
    def get_searchable_text(self) -> str:
        """獲取可搜尋的文本"""
        if self.shrine_info:
            return self.shrine_info.get_searchable_text()
        elif self.location_info:
            return self.location_info.get_searchable_text()
        else:
            return self.base_info.get_searchable_text()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        result = {
            "id": self.base_info.id,
            "category": self.category.value,
            "primary_name": self.primary_name,
            "coordinates": self.coordinates.to_dict(),
            "all_tags": [tag.value for tag in self.all_tags],
            "base_info": self.base_info.to_dict()
        }
        
        if self.shrine_info:
            result["shrine_info"] = self.shrine_info.to_dict()
        
        if self.location_info:
            result["location_info"] = self.location_info.to_dict()
        
        return result
    
    @classmethod
    def from_shrine(cls, shrine: ShrineInfo) -> 'UnifiedLocation':
        """從神社資料創建統一地點"""
        return cls(
            base_info=shrine,  # ShrineInfo 繼承自 LocationBase
            shrine_info=shrine
        )
    
    @classmethod
    def from_location(cls, location: TouristLocation) -> 'UnifiedLocation':
        """從景點資料創建統一地點"""
        return cls(
            base_info=location,  # TouristLocation 繼承自 LocationBase
            location_info=location
        )
    
    def __str__(self) -> str:
        """字串表示"""
        return f"{self.category.value}: {self.primary_name} ({self.coordinates.latitude}, {self.coordinates.longitude})"