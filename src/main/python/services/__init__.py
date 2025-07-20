"""
服務模組 - 提供向量搜尋、地理柵欄和其他核心服務
"""

from .vector_db import (
    VectorDatabase,
    VectorSearchService, 
    VectorDBConfig,
    SearchResult,
    create_vector_db
)

from .geofencing import (
    GeofenceManager,
    GeofenceZone,
    GeofenceEvent,
    Coordinates,
    FenceType,
    TriggerType,
    GeoUtils,
    create_geofence_manager
)

__all__ = [
    'VectorDatabase',
    'VectorSearchService',
    'VectorDBConfig', 
    'SearchResult',
    'create_vector_db',
    'GeofenceManager',
    'GeofenceZone',
    'GeofenceEvent',
    'Coordinates',
    'FenceType',
    'TriggerType',
    'GeoUtils',
    'create_geofence_manager'
]