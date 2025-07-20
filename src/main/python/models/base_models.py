"""
基礎資料模型
提供所有其他模型的共用結構和功能
"""

from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


@dataclass
class CoordinateInfo:
    """座標資訊"""
    latitude: float
    longitude: float
    geohash: Optional[str] = None
    accuracy: Optional[str] = None  # GPS精確度描述
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.latitude,
            "lon": self.longitude,
            "geohash": self.geohash,
            "accuracy": self.accuracy
        }


@dataclass
class BusinessHours:
    """營業時間資訊"""
    is_24_hours: bool = False
    is_closed: bool = False
    weekday_text: List[str] = field(default_factory=list)
    special_hours: Dict[str, str] = field(default_factory=dict)  # 特殊時間說明
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_24_hours": self.is_24_hours,
            "is_closed": self.is_closed,
            "weekday_text": self.weekday_text,
            "special_hours": self.special_hours
        }


@dataclass
class ContactInfo:
    """聯絡資訊"""
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    social_media: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "social_media": self.social_media
        }


class TagCategory(Enum):
    """標籤分類"""
    # 適合族群
    FAMILY_FRIENDLY = "親子友善"
    ELDERLY_FRIENDLY = "銀髮友善"
    ACCESSIBLE = "無障礙設施"
    PET_FRIENDLY = "寵物友善"
    
    # 季節特色
    SPRING_CHERRY = "賞櫻名所"
    SUMMER_FESTIVAL = "夏日祭典"
    AUTUMN_FOLIAGE = "賞楓景點"
    WINTER_SNOW = "雪景勝地"
    
    # 體驗類型
    SPIRITUAL = "能量景點"
    HISTORICAL = "歷史古蹟"
    NATURE = "自然景觀"
    CULTURAL = "文化體驗"
    GOURMET = "美食景點"
    SHOPPING = "購物天堂"
    
    # 實用資訊
    FREE_ADMISSION = "免費參觀"
    INDOOR_ACTIVITY = "雨天備案"
    PARKING_AVAILABLE = "停車便利"
    PUBLIC_TRANSPORT = "大眾運輸"
    
    # 特殊功能
    PRAYER_LUCK = "祈求好運"
    PRAYER_HEALTH = "祈求健康"
    PRAYER_LOVE = "祈求戀愛"
    PRAYER_BUSINESS = "事業成功"
    GOSHUIN_AVAILABLE = "御朱印"


@dataclass
class TaggedEntity:
    """帶標籤的實體基類"""
    tags: List[TagCategory] = field(default_factory=list)
    custom_tags: List[str] = field(default_factory=list)  # 自定義標籤
    
    def add_tag(self, tag: Union[TagCategory, str]):
        """添加標籤"""
        if isinstance(tag, TagCategory):
            if tag not in self.tags:
                self.tags.append(tag)
        else:
            if tag not in self.custom_tags:
                self.custom_tags.append(tag)
    
    def get_all_tags(self) -> List[str]:
        """獲取所有標籤（包含自定義）"""
        return [tag.value for tag in self.tags] + self.custom_tags
    
    def has_tag(self, tag: Union[TagCategory, str]) -> bool:
        """檢查是否包含特定標籤"""
        if isinstance(tag, TagCategory):
            return tag in self.tags
        return tag in self.custom_tags


@dataclass 
class LocationBase(TaggedEntity):
    """地點基礎資訊"""
    # 基本識別
    id: str
    name_jp: str
    name_en: Optional[str] = None
    name_local: Optional[str] = None
    
    # 地理位置
    prefecture: str
    city: str
    address: str
    coordinates: CoordinateInfo
    
    # 基本資訊
    description: Optional[str] = None
    description_en: Optional[str] = None
    
    # 聯絡與營業
    contact: ContactInfo = field(default_factory=ContactInfo)
    business_hours: BusinessHours = field(default_factory=BusinessHours)
    
    # 元數據
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    data_source: str = "manual"  # manual, google_maps, crawled
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "id": self.id,
            "name_jp": self.name_jp,
            "name_en": self.name_en,
            "name_local": self.name_local,
            "prefecture": self.prefecture,
            "city": self.city,
            "address": self.address,
            "coordinates": self.coordinates.to_dict(),
            "description": self.description,
            "description_en": self.description_en,
            "contact": self.contact.to_dict(),
            "business_hours": self.business_hours.to_dict(),
            "tags": self.get_all_tags(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "data_source": self.data_source
        }
    
    def get_searchable_text(self) -> str:
        """獲取可搜尋的文本內容"""
        text_parts = [
            self.name_jp,
            self.name_en or "",
            self.name_local or "",
            self.city,
            self.address,
            self.description or "",
            self.description_en or ""
        ]
        
        # 加入標籤文本
        text_parts.extend(self.get_all_tags())
        
        return " ".join(filter(None, text_parts))