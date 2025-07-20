"""
神社專用資料模型
處理神社特有的資訊如祭神、祭典、文化財等
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .base_models import LocationBase, TagCategory


@dataclass
class Deity:
    """祭神資訊"""
    name: str
    role: str  # 神明職能
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description
        }


@dataclass
class Festival:
    """祭典活動資訊"""
    name: str
    date: str  # 可能是具體日期或月份描述
    description: Optional[str] = None
    is_major: bool = False  # 是否為重大祭典
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "date": self.date,
            "description": self.description,
            "is_major": self.is_major
        }


@dataclass
class CulturalProperty:
    """文化財產資訊"""
    name: str
    category: str  # 文化財分類
    designation_level: str  # 指定層級（國寶、重要文化財等）
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "designation_level": self.designation_level,
            "description": self.description
        }


@dataclass
class ShrineInfo(LocationBase):
    """神社完整資訊"""
    # 神社特定資訊
    shrine_type: str = "神社"  # 神社、寺、その他
    romaji: Optional[str] = None
    
    # 歷史資訊
    founded_year: Optional[str] = None
    founder: Optional[str] = None
    historical_events: List[str] = field(default_factory=list)
    
    # 建築與文化
    architectural_style: Optional[str] = None
    cultural_properties: List[CulturalProperty] = field(default_factory=list)
    unesco_heritage: bool = False
    
    # 宗教資訊
    enshrined_deities: List[Deity] = field(default_factory=list)
    prayer_categories: List[str] = field(default_factory=list)
    
    # 參拜資訊
    admission_fee: float = 0.0
    omamori_types: List[str] = field(default_factory=list)  # 御守類型
    goshuin_available: bool = False  # 是否提供御朱印
    
    # 活動與祭典
    annual_festivals: List[Festival] = field(default_factory=list)
    ceremonies: List[str] = field(default_factory=list)
    
    # 交通資訊
    nearest_station: Optional[str] = None
    access_time_walk: Optional[str] = None
    bus_info: Optional[str] = None
    parking_info: Optional[str] = None
    
    def __post_init__(self):
        """初始化後自動設定標籤"""
        super().__post_init__()
        self._auto_assign_tags()
    
    def _auto_assign_tags(self):
        """根據神社資訊自動分配標籤"""
        # 根據祭神自動分配祈願標籤
        deity_roles = [deity.role.lower() for deity in self.enshrined_deities]
        
        if any("縁結び" in role or "恋愛" in role for role in deity_roles):
            self.add_tag(TagCategory.PRAYER_LOVE)
        
        if any("商売" in role or "事業" in role or "商業" in role for role in deity_roles):
            self.add_tag(TagCategory.PRAYER_BUSINESS)
        
        if any("健康" in role or "病気" in role for role in deity_roles):
            self.add_tag(TagCategory.PRAYER_HEALTH)
        
        # 根據文化財自動分配歷史標籤
        if self.cultural_properties or self.unesco_heritage:
            self.add_tag(TagCategory.HISTORICAL)
        
        # 根據費用分配標籤
        if self.admission_fee == 0:
            self.add_tag(TagCategory.FREE_ADMISSION)
        
        # 御朱印標籤
        if self.goshuin_available:
            self.add_tag(TagCategory.GOSHUIN_AVAILABLE)
        
        # 停車資訊
        if self.parking_info and "有" in self.parking_info:
            self.add_tag(TagCategory.PARKING_AVAILABLE)
        
        # 能量景點（所有神社都算）
        self.add_tag(TagCategory.SPIRITUAL)
    
    def get_main_deity(self) -> Optional[Deity]:
        """獲取主祭神"""
        return self.enshrined_deities[0] if self.enshrined_deities else None
    
    def get_major_festivals(self) -> List[Festival]:
        """獲取主要祭典"""
        return [f for f in self.annual_festivals if f.is_major]
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        base_dict = super().to_dict()
        
        shrine_dict = {
            "shrine_type": self.shrine_type,
            "romaji": self.romaji,
            "founded_year": self.founded_year,
            "founder": self.founder,
            "historical_events": self.historical_events,
            "architectural_style": self.architectural_style,
            "cultural_properties": [cp.to_dict() for cp in self.cultural_properties],
            "unesco_heritage": self.unesco_heritage,
            "enshrined_deities": [deity.to_dict() for deity in self.enshrined_deities],
            "prayer_categories": self.prayer_categories,
            "admission_fee": self.admission_fee,
            "omamori_types": self.omamori_types,
            "goshuin_available": self.goshuin_available,
            "annual_festivals": [f.to_dict() for f in self.annual_festivals],
            "ceremonies": self.ceremonies,
            "nearest_station": self.nearest_station,
            "access_time_walk": self.access_time_walk,
            "bus_info": self.bus_info,
            "parking_info": self.parking_info
        }
        
        # 合併基礎資料和神社特定資料
        base_dict.update(shrine_dict)
        return base_dict
    
    def get_searchable_text(self) -> str:
        """獲取可搜尋的文本內容"""
        base_text = super().get_searchable_text()
        
        # 添加神社特定的搜尋文本
        shrine_texts = [
            self.romaji or "",
            self.shrine_type,
            self.architectural_style or "",
            self.founder or "",
            " ".join(self.historical_events),
            " ".join(self.prayer_categories),
            " ".join(self.omamori_types),
            " ".join(self.ceremonies),
            self.nearest_station or "",
            self.bus_info or "",
            self.parking_info or ""
        ]
        
        # 添加祭神資訊
        for deity in self.enshrined_deities:
            shrine_texts.extend([deity.name, deity.role, deity.description or ""])
        
        # 添加祭典資訊
        for festival in self.annual_festivals:
            shrine_texts.extend([festival.name, festival.description or ""])
        
        # 添加文化財資訊
        for cp in self.cultural_properties:
            shrine_texts.extend([cp.name, cp.category, cp.description or ""])
        
        all_text = base_text + " " + " ".join(filter(None, shrine_texts))
        return all_text.strip()