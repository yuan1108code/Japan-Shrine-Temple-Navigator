"""
地理柵欄服務模組
實現基於地理位置的觸發和通知功能
"""

import math
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

import geohash

logger = logging.getLogger(__name__)


class FenceType(Enum):
    """柵欄類型"""
    CIRCULAR = "circular"
    RECTANGULAR = "rectangular"
    POLYGON = "polygon"


class TriggerType(Enum):
    """觸發類型"""
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"


@dataclass
class Coordinates:
    """座標資料結構"""
    latitude: float
    longitude: float
    
    def to_dict(self) -> Dict[str, float]:
        return {"latitude": self.latitude, "longitude": self.longitude}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Coordinates':
        return cls(latitude=data["latitude"], longitude=data["longitude"])


@dataclass
class GeofenceZone:
    """地理柵欄區域"""
    zone_id: str
    name: str
    fence_type: FenceType
    center: Coordinates
    radius: Optional[float] = None  # 圓形柵欄半徑（公尺）
    bounds: Optional[List[Coordinates]] = None  # 多邊形柵欄邊界
    location_ids: List[str] = None  # 關聯的地點 ID
    triggers: List[TriggerType] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.location_ids is None:
            self.location_ids = []
        if self.triggers is None:
            self.triggers = [TriggerType.ENTER]
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "fence_type": self.fence_type.value,
            "center": self.center.to_dict(),
            "radius": self.radius,
            "bounds": [b.to_dict() for b in self.bounds] if self.bounds else None,
            "location_ids": self.location_ids,
            "triggers": [t.value for t in self.triggers],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GeofenceZone':
        return cls(
            zone_id=data["zone_id"],
            name=data["name"],
            fence_type=FenceType(data["fence_type"]),
            center=Coordinates.from_dict(data["center"]),
            radius=data.get("radius"),
            bounds=[Coordinates.from_dict(b) for b in data["bounds"]] if data.get("bounds") else None,
            location_ids=data.get("location_ids", []),
            triggers=[TriggerType(t) for t in data.get("triggers", ["enter"])],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now()
        )


@dataclass
class GeofenceEvent:
    """地理柵欄事件"""
    event_id: str
    zone_id: str
    trigger_type: TriggerType
    user_location: Coordinates
    timestamp: datetime
    user_id: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "zone_id": self.zone_id,
            "trigger_type": self.trigger_type.value,
            "user_location": self.user_location.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "additional_data": self.additional_data
        }


class GeoUtils:
    """地理計算工具"""
    
    @staticmethod
    def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        """計算兩點間距離（公尺）"""
        R = 6371000  # 地球半徑（公尺）
        
        lat1_rad = math.radians(coord1.latitude)
        lat2_rad = math.radians(coord2.latitude)
        delta_lat = math.radians(coord2.latitude - coord1.latitude)
        delta_lon = math.radians(coord2.longitude - coord1.longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def point_in_circle(point: Coordinates, center: Coordinates, radius: float) -> bool:
        """檢查點是否在圓形區域內"""
        distance = GeoUtils.haversine_distance(point, center)
        return distance <= radius
    
    @staticmethod
    def point_in_rectangle(point: Coordinates, bounds: List[Coordinates]) -> bool:
        """檢查點是否在矩形區域內"""
        if len(bounds) != 2:
            return False
        
        min_lat = min(bounds[0].latitude, bounds[1].latitude)
        max_lat = max(bounds[0].latitude, bounds[1].latitude)
        min_lon = min(bounds[0].longitude, bounds[1].longitude)
        max_lon = max(bounds[0].longitude, bounds[1].longitude)
        
        return (min_lat <= point.latitude <= max_lat and 
                min_lon <= point.longitude <= max_lon)
    
    @staticmethod
    def point_in_polygon(point: Coordinates, bounds: List[Coordinates]) -> bool:
        """檢查點是否在多邊形區域內（射線法）"""
        if len(bounds) < 3:
            return False
        
        x, y = point.longitude, point.latitude
        n = len(bounds)
        inside = False
        
        p1x, p1y = bounds[0].longitude, bounds[0].latitude
        for i in range(1, n + 1):
            p2x, p2y = bounds[i % n].longitude, bounds[i % n].latitude
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    @staticmethod
    def generate_geohash(coord: Coordinates, precision: int = 8) -> str:
        """生成地理哈希"""
        return geohash.encode(coord.latitude, coord.longitude, precision)
    
    @staticmethod
    def decode_geohash(hash_str: str) -> Coordinates:
        """解碼地理哈希"""
        lat, lon = geohash.decode(hash_str)
        return Coordinates(latitude=lat, longitude=lon)


class GeofenceManager:
    """地理柵欄管理器"""
    
    def __init__(self):
        self.zones: Dict[str, GeofenceZone] = {}
        self.user_states: Dict[str, Dict[str, Any]] = {}  # 用戶狀態追蹤
        self.event_history: List[GeofenceEvent] = []
        
        logger.info("Geofence manager initialized")
    
    def create_zone(self, zone: GeofenceZone) -> bool:
        """創建地理柵欄區域"""
        try:
            if zone.zone_id in self.zones:
                logger.warning(f"Zone {zone.zone_id} already exists")
                return False
            
            # 驗證區域參數
            if zone.fence_type == FenceType.CIRCULAR and not zone.radius:
                raise ValueError("Circular fence requires radius")
            
            if zone.fence_type in [FenceType.RECTANGULAR, FenceType.POLYGON] and not zone.bounds:
                raise ValueError(f"{zone.fence_type.value} fence requires bounds")
            
            self.zones[zone.zone_id] = zone
            logger.info(f"Created geofence zone: {zone.zone_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating zone {zone.zone_id}: {e}")
            return False
    
    def delete_zone(self, zone_id: str) -> bool:
        """刪除地理柵欄區域"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            logger.info(f"Deleted geofence zone: {zone_id}")
            return True
        return False
    
    def get_zone(self, zone_id: str) -> Optional[GeofenceZone]:
        """獲取地理柵欄區域"""
        return self.zones.get(zone_id)
    
    def list_zones(self) -> List[GeofenceZone]:
        """列出所有地理柵欄區域"""
        return list(self.zones.values())
    
    def check_location(self, user_id: str, location: Coordinates) -> List[GeofenceEvent]:
        """檢查用戶位置並觸發相應事件"""
        events = []
        current_time = datetime.now()
        
        # 初始化用戶狀態
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "current_zones": set(),
                "last_location": None,
                "last_check": None
            }
        
        user_state = self.user_states[user_id]
        previous_zones = user_state["current_zones"].copy()
        current_zones = set()
        
        # 檢查每個區域
        for zone in self.zones.values():
            is_inside = self._is_point_in_zone(location, zone)
            
            if is_inside:
                current_zones.add(zone.zone_id)
                
                # 進入事件
                if (zone.zone_id not in previous_zones and 
                    TriggerType.ENTER in zone.triggers):
                    event = GeofenceEvent(
                        event_id=f"{user_id}_{zone.zone_id}_{current_time.timestamp()}",
                        zone_id=zone.zone_id,
                        trigger_type=TriggerType.ENTER,
                        user_location=location,
                        timestamp=current_time,
                        user_id=user_id,
                        additional_data={
                            "zone_name": zone.name,
                            "location_ids": zone.location_ids
                        }
                    )
                    events.append(event)
                    self.event_history.append(event)
        
        # 檢查離開事件
        for zone_id in previous_zones:
            if zone_id not in current_zones:
                zone = self.zones.get(zone_id)
                if zone and TriggerType.EXIT in zone.triggers:
                    event = GeofenceEvent(
                        event_id=f"{user_id}_{zone_id}_{current_time.timestamp()}_exit",
                        zone_id=zone_id,
                        trigger_type=TriggerType.EXIT,
                        user_location=location,
                        timestamp=current_time,
                        user_id=user_id,
                        additional_data={
                            "zone_name": zone.name,
                            "location_ids": zone.location_ids
                        }
                    )
                    events.append(event)
                    self.event_history.append(event)
        
        # 更新用戶狀態
        user_state["current_zones"] = current_zones
        user_state["last_location"] = location
        user_state["last_check"] = current_time
        
        if events:
            logger.info(f"Generated {len(events)} geofence events for user {user_id}")
        
        return events
    
    def _is_point_in_zone(self, point: Coordinates, zone: GeofenceZone) -> bool:
        """檢查點是否在指定區域內"""
        if zone.fence_type == FenceType.CIRCULAR:
            return GeoUtils.point_in_circle(point, zone.center, zone.radius)
        elif zone.fence_type == FenceType.RECTANGULAR:
            return GeoUtils.point_in_rectangle(point, zone.bounds)
        elif zone.fence_type == FenceType.POLYGON:
            return GeoUtils.point_in_polygon(point, zone.bounds)
        return False
    
    def get_nearby_zones(self, location: Coordinates, max_distance: float = 1000) -> List[Tuple[GeofenceZone, float]]:
        """獲取附近的地理柵欄區域"""
        nearby = []
        
        for zone in self.zones.values():
            distance = GeoUtils.haversine_distance(location, zone.center)
            
            # 對於圓形區域，考慮半徑
            if zone.fence_type == FenceType.CIRCULAR:
                effective_distance = max(0, distance - zone.radius)
            else:
                effective_distance = distance
            
            if effective_distance <= max_distance:
                nearby.append((zone, distance))
        
        # 按距離排序
        nearby.sort(key=lambda x: x[1])
        return nearby
    
    def get_user_current_zones(self, user_id: str) -> List[str]:
        """獲取用戶當前所在的區域"""
        if user_id in self.user_states:
            return list(self.user_states[user_id]["current_zones"])
        return []
    
    def get_event_history(self, user_id: Optional[str] = None, 
                         zone_id: Optional[str] = None,
                         hours: int = 24) -> List[GeofenceEvent]:
        """獲取事件歷史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_events = []
        for event in self.event_history:
            if event.timestamp < cutoff_time:
                continue
            
            if user_id and event.user_id != user_id:
                continue
            
            if zone_id and event.zone_id != zone_id:
                continue
            
            filtered_events.append(event)
        
        return filtered_events
    
    def create_location_zones(self, locations: List[Dict[str, Any]], 
                            default_radius: float = 100) -> List[GeofenceZone]:
        """為地點創建地理柵欄區域"""
        created_zones = []
        
        for location in locations:
            try:
                coords = location.get("coordinates", {})
                if not coords or "lat" not in coords or "lng" not in coords:
                    continue
                
                zone_id = f"location_{location.get('id', 'unknown')}"
                zone_name = f"{location.get('primary_name', '未知地點')} 區域"
                
                zone = GeofenceZone(
                    zone_id=zone_id,
                    name=zone_name,
                    fence_type=FenceType.CIRCULAR,
                    center=Coordinates(
                        latitude=coords["lat"],
                        longitude=coords["lng"]
                    ),
                    radius=default_radius,
                    location_ids=[location.get("id")],
                    triggers=[TriggerType.ENTER, TriggerType.EXIT],
                    metadata={
                        "location_name": location.get("primary_name"),
                        "category": location.get("category"),
                        "auto_generated": True
                    }
                )
                
                if self.create_zone(zone):
                    created_zones.append(zone)
                    
            except Exception as e:
                logger.error(f"Error creating zone for location {location.get('id')}: {e}")
        
        logger.info(f"Created {len(created_zones)} location-based geofence zones")
        return created_zones
    
    def export_zones(self, file_path: str) -> bool:
        """匯出地理柵欄配置"""
        try:
            export_data = {
                "zones": [zone.to_dict() for zone in self.zones.values()],
                "export_timestamp": datetime.now().isoformat(),
                "total_zones": len(self.zones)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(self.zones)} zones to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting zones: {e}")
            return False
    
    def import_zones(self, file_path: str) -> bool:
        """匯入地理柵欄配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_count = 0
            for zone_data in import_data.get("zones", []):
                zone = GeofenceZone.from_dict(zone_data)
                if self.create_zone(zone):
                    imported_count += 1
            
            logger.info(f"Imported {imported_count} zones from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing zones: {e}")
            return False


# 工具函數
def create_geofence_manager() -> GeofenceManager:
    """創建地理柵欄管理器實例"""
    return GeofenceManager()


if __name__ == "__main__":
    # 測試地理柵欄功能
    logging.basicConfig(level=logging.INFO)
    
    # 創建管理器
    manager = GeofenceManager()
    
    # 測試座標（福井市附近）
    fukui_center = Coordinates(latitude=36.0612, longitude=136.2236)
    test_location = Coordinates(latitude=36.0620, longitude=136.2240)
    
    # 創建測試區域
    test_zone = GeofenceZone(
        zone_id="fukui_test",
        name="福井測試區域",
        fence_type=FenceType.CIRCULAR,
        center=fukui_center,
        radius=500,  # 500公尺
        triggers=[TriggerType.ENTER, TriggerType.EXIT]
    )
    
    # 測試功能
    success = manager.create_zone(test_zone)
    print(f"Zone creation: {'Success' if success else 'Failed'}")
    
    # 檢查位置
    events = manager.check_location("test_user", test_location)
    print(f"Generated events: {len(events)}")
    
    for event in events:
        print(f"Event: {event.trigger_type.value} in zone {event.zone_id}")
    
    # 獲取附近區域
    nearby = manager.get_nearby_zones(test_location, max_distance=1000)
    print(f"Nearby zones: {len(nearby)}")
    
    for zone, distance in nearby:
        print(f"Zone: {zone.name}, Distance: {distance:.1f}m")