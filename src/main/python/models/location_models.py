"""
一般景點資料模型
處理觀光景點、道の駅、餐廳等場所的資訊
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .base_models import LocationBase, TagCategory


@dataclass
class Photo:
    """照片資訊"""
    url: str
    reference: Optional[str] = None  # Google Maps photo reference
    width: Optional[int] = None
    height: Optional[int] = None
    attribution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "reference": self.reference,
            "width": self.width,
            "height": self.height,
            "attribution": self.attribution
        }


@dataclass
class Review:
    """使用者評論"""
    author_name: str
    rating: float
    text: str
    time: int  # Unix timestamp
    language: Optional[str] = "ja"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "author_name": self.author_name,
            "rating": self.rating,
            "text": self.text,
            "time": self.time,
            "language": self.language
        }


@dataclass
class GoogleMapsData:
    """Google Maps 整合資料"""
    place_id: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None  # 0-4 價格等級
    photos: List[Photo] = field(default_factory=list)
    reviews: List[Review] = field(default_factory=list)
    types: List[str] = field(default_factory=list)  # Google Places types
    business_status: str = "OPERATIONAL"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "place_id": self.place_id,
            "rating": self.rating,
            "user_ratings_total": self.user_ratings_total,
            "price_level": self.price_level,
            "photos": [photo.to_dict() for photo in self.photos],
            "reviews": [review.to_dict() for review in self.reviews],
            "types": self.types,
            "business_status": self.business_status
        }


@dataclass
class TouristLocation(LocationBase):
    """觀光景點資訊"""
    # 場所類型
    location_type: str = "tourist_spot"  # tourist_spot, restaurant, shopping, etc.
    category: Optional[str] = None  # 更具體的分類
    
    # Google Maps 整合
    google_data: Optional[GoogleMapsData] = None
    
    # 費用資訊
    admission_fee: Optional[float] = None
    price_range: Optional[str] = None  # 價格範圍描述
    
    # 設施資訊
    facilities: List[str] = field(default_factory=list)
    accessibility: List[str] = field(default_factory=list)
    
    # 特色與體驗
    highlights: List[str] = field(default_factory=list)
    activities: List[str] = field(default_factory=list)
    
    # 季節資訊
    best_season: List[str] = field(default_factory=list)
    seasonal_notes: Dict[str, str] = field(default_factory=dict)
    
    # 交通資訊
    access_methods: List[str] = field(default_factory=list)
    parking_info: Optional[str] = None
    
    def __post_init__(self):
        """初始化後自動設定標籤"""
        self._auto_assign_tags()
    
    def _auto_assign_tags(self):
        """根據景點資訊自動分配標籤"""
        # 根據費用分配標籤
        if self.admission_fee == 0 or (
            self.admission_fee is None and 
            self.google_data and 
            self.google_data.price_level == 0
        ):
            self.add_tag(TagCategory.FREE_ADMISSION)
        
        # 根據設施分配標籤
        facility_text = " ".join(self.facilities).lower()
        
        if "駐車場" in facility_text or "parking" in facility_text:
            self.add_tag(TagCategory.PARKING_AVAILABLE)
        
        if "バリアフリー" in facility_text or "車椅子" in facility_text:
            self.add_tag(TagCategory.ACCESSIBLE)
        
        if "子供" in facility_text or "キッズ" in facility_text:
            self.add_tag(TagCategory.FAMILY_FRIENDLY)
        
        # 根據類型分配標籤
        if self.location_type == "restaurant":
            self.add_tag(TagCategory.GOURMET)
        elif self.location_type == "shopping":
            self.add_tag(TagCategory.SHOPPING)
        
        # 根據 Google Maps 類型分配標籤
        if self.google_data:
            google_types = " ".join(self.google_data.types).lower()
            
            if "museum" in google_types or "historical" in google_types:
                self.add_tag(TagCategory.HISTORICAL)
            
            if "park" in google_types or "natural" in google_types:
                self.add_tag(TagCategory.NATURE)
            
            if "restaurant" in google_types or "food" in google_types:
                self.add_tag(TagCategory.GOURMET)
        
        # 根據季節資訊分配標籤
        season_text = " ".join(self.best_season + list(self.seasonal_notes.values())).lower()
        
        if "桜" in season_text or "cherry" in season_text:
            self.add_tag(TagCategory.SPRING_CHERRY)
        
        if "紅葉" in season_text or "autumn" in season_text:
            self.add_tag(TagCategory.AUTUMN_FOLIAGE)
        
        if "雪" in season_text or "snow" in season_text:
            self.add_tag(TagCategory.WINTER_SNOW)
        
        # 室內活動判斷
        if "室內" in " ".join(self.highlights + self.activities):
            self.add_tag(TagCategory.INDOOR_ACTIVITY)
    
    def get_average_rating(self) -> Optional[float]:
        """獲取平均評分"""
        return self.google_data.rating if self.google_data else None
    
    def get_price_level_text(self) -> Optional[str]:
        """獲取價格等級文字描述"""
        if not self.google_data or self.google_data.price_level is None:
            return None
        
        levels = {
            0: "免費",
            1: "便宜",
            2: "中等",
            3: "昂貴",
            4: "非常昂貴"
        }
        
        return levels.get(self.google_data.price_level, "未知")
    
    def get_recent_reviews(self, limit: int = 5) -> List[Review]:
        """獲取最近的評論"""
        if not self.google_data:
            return []
        
        sorted_reviews = sorted(
            self.google_data.reviews, 
            key=lambda r: r.time, 
            reverse=True
        )
        
        return sorted_reviews[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        base_dict = super().to_dict()
        
        location_dict = {
            "location_type": self.location_type,
            "category": self.category,
            "google_data": self.google_data.to_dict() if self.google_data else None,
            "admission_fee": self.admission_fee,
            "price_range": self.price_range,
            "facilities": self.facilities,
            "accessibility": self.accessibility,
            "highlights": self.highlights,
            "activities": self.activities,
            "best_season": self.best_season,
            "seasonal_notes": self.seasonal_notes,
            "access_methods": self.access_methods,
            "parking_info": self.parking_info
        }
        
        base_dict.update(location_dict)
        return base_dict
    
    def get_searchable_text(self) -> str:
        """獲取可搜尋的文本內容"""
        base_text = super().get_searchable_text()
        
        # 添加景點特定的搜尋文本
        location_texts = [
            self.location_type,
            self.category or "",
            self.price_range or "",
            " ".join(self.facilities),
            " ".join(self.accessibility),
            " ".join(self.highlights),
            " ".join(self.activities),
            " ".join(self.best_season),
            " ".join(self.seasonal_notes.values()),
            " ".join(self.access_methods),
            self.parking_info or ""
        ]
        
        # 添加 Google Maps 評論內容
        if self.google_data:
            location_texts.extend([" ".join(self.google_data.types)])
            
            # 添加評論文本（取最近的幾則）
            for review in self.get_recent_reviews(3):
                location_texts.append(review.text)
        
        all_text = base_text + " " + " ".join(filter(None, location_texts))
        return all_text.strip()