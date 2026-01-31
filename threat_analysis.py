# -*- coding: utf-8 -*-
"""
Threat Analysis Module for NEPTUN API
Contains: Threat Tracking, Channel Intelligence Fusion, Trajectory Builder

Extracted from app.py to reduce main file size.
"""

import hashlib
import math
import os
import re
import threading
import time as time_module
from collections import defaultdict
from datetime import datetime, timedelta

# ==================== AI SMART TTL SYSTEM ====================
# Intelligent marker lifetime calculation based on threat type, context, and status

# Base TTL in minutes - MINIMUM time, adjusted UP based on distance/ETA
THREAT_BASE_TTL = {
    'shahed': 20, 'drone': 18, 'fpv': 5, 'rozved': 15, 'cruise': 15,
    'ballistic': 4, 'kab': 6, 'rocket': 6, 'kinzhal': 2, 'iskander': 4,
    'kalibr': 18, 'x101': 25, 'x22': 10, 'unknown': 25, 'explosion': 8,
    'artillery': 5, 'air': 20, 'avia': 12, 'rszv': 5, 'obstril': 5, 'pusk': 8,
}

# Maximum TTL by threat type
THREAT_MAX_TTL = {
    'shahed': 240, 'drone': 180, 'fpv': 10, 'rozved': 60, 'cruise': 50,
    'ballistic': 12, 'kab': 15, 'rocket': 12, 'kinzhal': 6, 'iskander': 10,
    'kalibr': 60, 'x101': 90, 'x22': 30, 'unknown': 60, 'explosion': 15,
    'artillery': 10, 'air': 45, 'avia': 30, 'rszv': 10, 'obstril': 10, 'pusk': 25,
}

# Keywords for distance detection
DISTANT_KEYWORDS = [
    'чорне море', 'каспій', 'азовськ', 'білорусь', 'росія', 'брянськ',
    'бєлгород', 'курськ', 'ростов', 'криворіж', 'крим', 'керч',
    'запуск', 'старт', 'пуск', 'зліт', 'виявлен', 'увійшл', 'зафіксован',
]

CLOSE_KEYWORDS = [
    'над ', 'в районі', 'біля', 'поблизу', 'наближається до',
    'на підльоті до', 'вже в', 'вже над', 'досяг', 'прибув',
]

THREAT_ENDED_KEYWORDS = [
    'збит', 'збито', 'знищен', 'уражен', 'ліквідован', 'нейтралізован',
    'перехоплен', 'відбит', 'пішов', 'покинув', 'вийшов', 'минув',
    'завершен', 'закінч', 'скасуван', 'відбій', 'чисто',
]

THREAT_ACTIVE_KEYWORDS = [
    'курс', 'курсом', 'напрям', 'рухається', 'летить', 'прямує',
    'наближається', 'атак', 'загроз', 'увага', 'обережно',
    'пуск', 'старт', 'виявлен', 'тривога', 'терміново', 'укриття',
]

MAJOR_CITIES = {
    'київ': (50.4501, 30.5234), 'харків': (49.9935, 36.2304),
    'одеса': (46.4825, 30.7233), 'дніпро': (48.4647, 35.0462),
    'львів': (49.8397, 24.0297), 'запоріжжя': (47.8388, 35.1396),
    'миколаїв': (46.9750, 31.9946), 'полтава': (49.5883, 34.5514),
    'херсон': (46.6354, 32.6169), 'вінниця': (49.2331, 28.4682),
}

# Import THREAT_SPEEDS from main module (will be passed)
THREAT_SPEEDS = {}

def set_threat_speeds(speeds: dict):
    """Set THREAT_SPEEDS from main module"""
    global THREAT_SPEEDS
    THREAT_SPEEDS = speeds



def calculate_ai_marker_ttl(message_text: str, threat_type: str = None,
                            distance_km: float = None, eta_minutes: float = None,
                            source_region: str = None, marker_data: dict = None) -> dict:
    """Calculate intelligent TTL for a marker based on AI analysis."""
    msg_lower = (message_text or '').lower()
    
    # Check if threat ended
    ended_count = sum(1 for kw in THREAT_ENDED_KEYWORDS if kw in msg_lower)
    active_count = sum(1 for kw in THREAT_ACTIVE_KEYWORDS if kw in msg_lower)
    
    if ended_count >= 2 or (ended_count > 0 and active_count == 0):
        return {
            'ttl_minutes': 5, 'ttl_seconds': 300,
            'expires_at': datetime.now() + timedelta(minutes=5),
            'confidence': 0.9, 'reason': 'Загроза завершена', 'status': 'ended'
        }
    
    # Detect threat type from message
    if not threat_type:
        if 'пуск' in msg_lower: threat_type = 'pusk'
        elif any(w in msg_lower for w in ['кінжал', 'гіперзвук']): threat_type = 'kinzhal'
        elif any(w in msg_lower for w in ['балістик', 'іскандер']): threat_type = 'ballistic'
        elif any(w in msg_lower for w in ['шахед', 'герань']): threat_type = 'shahed'
        elif any(w in msg_lower for w in ['бпла', 'дрон']): threat_type = 'drone'
        elif any(w in msg_lower for w in ['крилат', 'калібр']): threat_type = 'cruise'
        elif any(w in msg_lower for w in ['каб', 'бомб']): threat_type = 'kab'
        else: threat_type = 'unknown'
    
    base_ttl = THREAT_BASE_TTL.get(threat_type, 25)
    max_ttl = THREAT_MAX_TTL.get(threat_type, 60)
    reason = f"🎯 {threat_type}"
    confidence = 0.7
    
    # Distance adjustment
    distant = sum(1 for kw in DISTANT_KEYWORDS if kw in msg_lower)
    close = sum(1 for kw in CLOSE_KEYWORDS if kw in msg_lower)
    
    if distant > close:
        factor = 3.0 if threat_type in ['shahed', 'drone'] else 1.5
        base_ttl *= factor
        reason += " 📍далеко"
    elif close > distant:
        base_ttl *= 0.7
        reason += " 📍близько"
    
    # ETA adjustment
    if eta_minutes and eta_minutes > 0:
        eta_buffer = eta_minutes * 1.4 + 8
        if eta_buffer > base_ttl:
            base_ttl = eta_buffer
            reason = f"⏱️ETA: {eta_minutes:.0f}хв"
    
    # Source region adjustment
    if source_region:
        src = source_region.lower()
        if 'море' in src: base_ttl = max(base_ttl, 120 if threat_type == 'shahed' else 50)
        elif 'білорусь' in src: base_ttl = max(base_ttl, 35)
        elif any(r in src for r in ['росія', 'брянськ', 'бєлгород']): base_ttl = max(base_ttl, 30)
    
    base_ttl = min(int(round(base_ttl / 5) * 5), max_ttl)
    base_ttl = max(5, base_ttl)
    
    return {
        'ttl_minutes': base_ttl, 'ttl_seconds': base_ttl * 60,
        'expires_at': datetime.now() + timedelta(minutes=base_ttl),
        'confidence': round(confidence, 2), 'reason': reason,
        'status': 'active', 'threat_type_detected': threat_type
    }

def get_marker_ttl_from_message(message: dict) -> dict:
    """Get TTL for a marker from message data."""
    text = message.get('text', '')
    threat_type = message.get('threat_type')
    trajectory = message.get('trajectory') or message.get('enhanced_trajectory')
    
    distance_km = trajectory.get('distance_km') if trajectory else None
    eta = trajectory.get('eta', {}) if trajectory else {}
    eta_minutes = eta.get('avg_minutes') if isinstance(eta, dict) else None
    source_region = message.get('source') or message.get('course_source')
    
    return calculate_ai_marker_ttl(text, threat_type, distance_km, eta_minutes, source_region, message)


# ==================== THREAT TRACKING SYSTEM ====================

ACTIVE_THREATS = {}
ACTIVE_THREATS_LOCK = threading.Lock()
REGION_THREATS = {}
_LAST_ALARM_STATES = {}

class ThreatTracker:
    """Real-time threat tracking system."""
    
    def __init__(self):
        self.threats = {}
        self.lock = threading.Lock()
        self.region_to_threats = {}
        self.message_to_threat = {}
    
    def generate_threat_id(self, msg_text: str, threat_type: str, region: str) -> str:
        key = f"{threat_type}:{region}:{datetime.now().strftime('%Y%m%d%H')}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def parse_threat_from_message(self, message: dict) -> dict:
        """Parse threat info from message."""
        text = message.get('text', '')
        msg_lower = text.lower()
        
        result = {
            'threat_type': None, 'quantity': 1, 'quantity_destroyed': 0,
            'regions': [], 'status': 'active', 'direction': None,
            'target': None, 'coordinates': None, 'original_message': message
        }
        
        # Detect threat type
        if 'пуск' in msg_lower: result['threat_type'] = 'pusk'
        elif any(w in msg_lower for w in ['шахед', 'герань']): result['threat_type'] = 'shahed'
        elif any(w in msg_lower for w in ['бпла', 'дрон']): result['threat_type'] = 'drone'
        elif any(w in msg_lower for w in ['балістик', 'іскандер']): result['threat_type'] = 'ballistic'
        elif any(w in msg_lower for w in ['крилат', 'калібр']): result['threat_type'] = 'cruise'
        elif any(w in msg_lower for w in ['каб', 'бомб']): result['threat_type'] = 'kab'
        else: result['threat_type'] = 'unknown'
        
        # Detect quantity
        qty_match = re.search(r'(\d+)\s*(?:шахед|бпла|дрон|ракет)', msg_lower)
        if qty_match: result['quantity'] = int(qty_match.group(1))
        
        # Detect destroyed
        destroyed_match = re.search(r'(\d+)\s*(?:збит|знищен)', msg_lower)
        if destroyed_match: result['quantity_destroyed'] = int(destroyed_match.group(1))
        
        # Detect status
        if any(w in msg_lower for w in THREAT_ENDED_KEYWORDS[:10]): result['status'] = 'destroyed'
        elif any(w in msg_lower for w in ['пролетів', 'минув', 'пройшов']): result['status'] = 'passed'
        
        return result
    
    def add_or_update_threat(self, message: dict) -> str:
        """Add new threat or update existing."""
        threat_info = self.parse_threat_from_message(message)
        threat_type = threat_info['threat_type']
        region = message.get('region', 'unknown')
        
        with self.lock:
            threat_id = self.generate_threat_id(message.get('text', ''), threat_type, region)
            
            if threat_id in self.threats:
                # Update existing
                existing = self.threats[threat_id]
                existing['last_update'] = datetime.now()
                existing['messages'].append(message)
                if threat_info['quantity_destroyed'] > existing.get('quantity_destroyed', 0):
                    existing['quantity_destroyed'] = threat_info['quantity_destroyed']
                if threat_info['status'] != 'active':
                    existing['status'] = threat_info['status']
            else:
                # Create new
                self.threats[threat_id] = {
                    'id': threat_id,
                    'threat_type': threat_type,
                    'quantity': threat_info['quantity'],
                    'quantity_destroyed': threat_info['quantity_destroyed'],
                    'status': threat_info['status'],
                    'region': region,
                    'created_at': datetime.now(),
                    'last_update': datetime.now(),
                    'messages': [message],
                    'coordinates': message.get('lat') and (message.get('lat'), message.get('lng'))
                }
                
                # Track by region
                if region not in self.region_to_threats:
                    self.region_to_threats[region] = set()
                self.region_to_threats[region].add(threat_id)
            
            return threat_id
    
    def get_active_threats(self, region: str = None) -> list:
        """Get list of active threats."""
        with self.lock:
            threats = []
            for t in self.threats.values():
                if t['status'] == 'active':
                    if region is None or region.lower() in t.get('region', '').lower():
                        threats.append(t.copy())
            return threats
    
    def remove_threats_by_region(self, region: str):
        """Remove threats when alarm ends in region."""
        with self.lock:
            region_lower = region.lower()
            to_remove = []
            for tid, t in self.threats.items():
                if region_lower in t.get('region', '').lower():
                    to_remove.append(tid)
            for tid in to_remove:
                del self.threats[tid]
            if region in self.region_to_threats:
                del self.region_to_threats[region]
    
    def cleanup_old_threats(self, max_age_minutes: int = 120):
        """Remove threats older than max_age."""
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        with self.lock:
            to_remove = [tid for tid, t in self.threats.items() if t['last_update'] < cutoff]
            for tid in to_remove:
                del self.threats[tid]


# Global instance
THREAT_TRACKER = ThreatTracker()


# ==================== CHANNEL INTELLIGENCE FUSION ====================

class ChannelIntelligenceFusion:
    """Multi-channel intelligence fusion for threat analysis."""
    
    def __init__(self):
        self.channel_reliability = defaultdict(lambda: 0.5)
        self.recent_reports = []
        self.lock = threading.Lock()
    
    def add_report(self, channel: str, message: dict, parsed_info: dict):
        """Add intelligence report from channel."""
        with self.lock:
            self.recent_reports.append({
                'channel': channel,
                'message': message,
                'parsed': parsed_info,
                'timestamp': datetime.now()
            })
            # Keep last 500 reports
            if len(self.recent_reports) > 500:
                self.recent_reports = self.recent_reports[-500:]
    
    def get_threat_confidence(self, threat_type: str, region: str, time_window_minutes: int = 15) -> float:
        """Calculate confidence based on multi-channel corroboration."""
        cutoff = datetime.now() - timedelta(minutes=time_window_minutes)
        
        with self.lock:
            relevant = [r for r in self.recent_reports 
                       if r['timestamp'] > cutoff 
                       and r['parsed'].get('threat_type') == threat_type
                       and region.lower() in str(r['parsed'].get('regions', [])).lower()]
        
        if not relevant: return 0.3
        
        # More channels = higher confidence
        channels = set(r['channel'] for r in relevant)
        base_confidence = min(0.5 + len(channels) * 0.15, 0.95)
        
        return base_confidence
    
    def fuse_threat_info(self, reports: list) -> dict:
        """Fuse multiple reports into single threat assessment."""
        if not reports: return {}
        
        # Aggregate quantities
        quantities = [r['parsed'].get('quantity', 1) for r in reports]
        destroyed = [r['parsed'].get('quantity_destroyed', 0) for r in reports]
        
        return {
            'quantity_estimate': max(quantities),
            'quantity_destroyed': max(destroyed),
            'confidence': min(0.5 + len(reports) * 0.1, 0.95),
            'source_channels': list(set(r['channel'] for r in reports)),
            'report_count': len(reports)
        }


# Global instance
CHANNEL_FUSION = ChannelIntelligenceFusion()


# ==================== TRAJECTORY BUILDER ====================

class TrajectoryBuilder:
    """Build and predict threat trajectories."""
    
    def __init__(self):
        self.known_routes = {}
        self.lock = threading.Lock()
    
    def build_trajectory(self, waypoints: list, threat_type: str = 'unknown') -> dict:
        """Build trajectory from waypoints."""
        if len(waypoints) < 2:
            return {'valid': False, 'reason': 'Not enough waypoints'}
        
        # Calculate distances and bearings
        total_distance = 0
        bearings = []
        
        for i in range(len(waypoints) - 1):
            p1, p2 = waypoints[i], waypoints[i+1]
            lat1, lon1 = p1.get('lat', p1[0] if isinstance(p1, tuple) else 0), p1.get('lng', p1[1] if isinstance(p1, tuple) else 0)
            lat2, lon2 = p2.get('lat', p2[0] if isinstance(p2, tuple) else 0), p2.get('lng', p2[1] if isinstance(p2, tuple) else 0)
            
            # Haversine distance
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            dist = R * 2 * math.asin(math.sqrt(a))
            total_distance += dist
            
            # Bearing
            y = math.sin(math.radians(lon2-lon1)) * math.cos(math.radians(lat2))
            x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2-lon1))
            bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
            bearings.append(bearing)
        
        avg_bearing = sum(bearings) / len(bearings) if bearings else 0
        
        # Get speed for threat type
        speeds = THREAT_SPEEDS.get(threat_type, {'avg': 400})
        eta_minutes = (total_distance / speeds.get('avg', 400)) * 60
        
        return {
            'valid': True,
            'waypoints': waypoints,
            'total_distance_km': round(total_distance, 1),
            'average_bearing': round(avg_bearing, 1),
            'bearing_direction': self._bearing_to_direction(avg_bearing),
            'eta_minutes': round(eta_minutes, 1),
            'threat_type': threat_type
        }
    
    def _bearing_to_direction(self, bearing: float) -> str:
        """Convert bearing to cardinal direction."""
        directions = ['Пн', 'ПнСх', 'Сх', 'ПдСх', 'Пд', 'ПдЗх', 'Зх', 'ПнЗх']
        idx = int((bearing + 22.5) / 45) % 8
        return directions[idx]
    
    def predict_target(self, trajectory: dict, possible_targets: dict) -> dict:
        """Predict most likely target based on trajectory."""
        if not trajectory.get('valid') or not possible_targets:
            return {'target': None, 'confidence': 0}
        
        bearing = trajectory.get('average_bearing', 0)
        last_point = trajectory['waypoints'][-1]
        lat = last_point.get('lat', last_point[0] if isinstance(last_point, tuple) else 0)
        lon = last_point.get('lng', last_point[1] if isinstance(last_point, tuple) else 0)
        
        best_target = None
        best_score = 0
        
        for name, coords in possible_targets.items():
            target_lat, target_lon = coords if isinstance(coords, tuple) else (coords.get('lat'), coords.get('lng'))
            
            # Calculate bearing to target
            y = math.sin(math.radians(target_lon - lon)) * math.cos(math.radians(target_lat))
            x = math.cos(math.radians(lat)) * math.sin(math.radians(target_lat)) - math.sin(math.radians(lat)) * math.cos(math.radians(target_lat)) * math.cos(math.radians(target_lon - lon))
            target_bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
            
            # Score based on bearing alignment
            bearing_diff = abs(bearing - target_bearing)
            if bearing_diff > 180: bearing_diff = 360 - bearing_diff
            
            score = max(0, 1 - bearing_diff / 45)  # Full score if within 45 degrees
            
            if score > best_score:
                best_score = score
                best_target = name
        
        return {
            'target': best_target,
            'confidence': round(best_score, 2),
            'bearing_to_target': bearing
        }


# Global instance
TRAJECTORY_BUILDER = TrajectoryBuilder()


# Export all
__all__ = [
    'THREAT_BASE_TTL', 'THREAT_MAX_TTL',
    'calculate_ai_marker_ttl', 'get_marker_ttl_from_message',
    'set_threat_speeds',
    'ThreatTracker', 'THREAT_TRACKER', 'ACTIVE_THREATS', 'ACTIVE_THREATS_LOCK',
    'ChannelIntelligenceFusion', 'CHANNEL_FUSION',
    'TrajectoryBuilder', 'TRAJECTORY_BUILDER',
]
