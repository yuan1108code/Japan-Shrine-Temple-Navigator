"""
福井旅遊資料模型
統一的資料結構支援神社、景點和地理查詢功能
"""

from .base_models import (
    LocationBase,
    CoordinateInfo,
    BusinessHours,
    ContactInfo,
    TaggedEntity
)

from .shrine_models import (
    ShrineInfo,
    Deity,
    Festival,
    CulturalProperty
)

from .location_models import (
    TouristLocation,
    Review,
    Photo,
    GoogleMapsData
)

from .unified_models import (
    UnifiedLocation,
    LocationCategory,
    TagCategory,
    GeoQuery,
    SearchResult
)

__all__ = [
    'LocationBase',
    'CoordinateInfo', 
    'BusinessHours',
    'ContactInfo',
    'TaggedEntity',
    'ShrineInfo',
    'Deity',
    'Festival',
    'CulturalProperty',
    'TouristLocation',
    'Review',
    'Photo',
    'GoogleMapsData',
    'UnifiedLocation',
    'LocationCategory',
    'TagCategory',
    'GeoQuery',
    'SearchResult'
]