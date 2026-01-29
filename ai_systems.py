# AI Systems Module - extracted from app.py
# Contains: AI Geocoding, AI Route, AI Prediction, Threat Tracking, Intelligence Fusion

import time
import re
import math
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Will be populated from app.py after import
GROQ_ENABLED = False
_groq_cache = {}
_groq_cache_ttl = 300
_groq_cache_max_size = 500  # MEMORY PROTECTION: Max cached AI responses
_groq_last_call = 0
_groq_min_interval = 0.5

def init_groq(enabled: bool, cache: dict, cache_ttl: int, min_interval: float):
    """Initialize Groq settings from app.py"""
    global GROQ_ENABLED, _groq_cache, _groq_cache_ttl, _groq_min_interval
    GROQ_ENABLED = enabled
    _groq_cache = cache
    _groq_cache_ttl = cache_ttl
    _groq_min_interval = min_interval

def _cleanup_groq_cache():
    """Clean up Groq cache to prevent memory growth"""
    global _groq_cache
    if len(_groq_cache) > _groq_cache_max_size:
        # Remove expired entries first
        now = time.time()
        _groq_cache = {k: v for k, v in _groq_cache.items() 
                       if isinstance(v, tuple) and len(v) > 1 and now - v[1] < _groq_cache_ttl}
        # If still too big, remove oldest half
        if len(_groq_cache) > _groq_cache_max_size:
            items = sorted(_groq_cache.items(), key=lambda x: x[1][1] if isinstance(x[1], tuple) else 0)
            _groq_cache = dict(items[len(items)//2:])


# Stub - will use the actual instance from app.py
groq_client = None

def set_groq_client(client):
    global groq_client
    groq_client = client

# ==================== THREAT TRACKER ====================

class ThreatTracker:
    """Intelligent threat tracking system"""
    
    def __init__(self):
        self.active_threats: Dict[str, dict] = {}
        self.threat_history: List[dict] = []
        self.max_history = 1000
        self._lock_time = 0
        
    def add_threat(self, threat_id: str, data: dict) -> bool:
        """Add or update a threat"""
        now = time.time()
        
        if threat_id in self.active_threats:
            existing = self.active_threats[threat_id]
            existing['last_seen'] = now
            existing['updates'] = existing.get('updates', 0) + 1
            if 'positions' in data:
                existing.setdefault('positions', []).extend(data['positions'])
            return False
        
        data['first_seen'] = now
        data['last_seen'] = now
        data['updates'] = 1
        self.active_threats[threat_id] = data
        return True
    
    def remove_threat(self, threat_id: str) -> Optional[dict]:
        """Remove and archive a threat"""
        if threat_id in self.active_threats:
            threat = self.active_threats.pop(threat_id)
            threat['removed_at'] = time.time()
            self.threat_history.append(threat)
            if len(self.threat_history) > self.max_history:
                self.threat_history = self.threat_history[-self.max_history:]
            return threat
        return None
    
    def get_active_by_region(self, region: str) -> List[dict]:
        """Get active threats in a region"""
        return [t for t in self.active_threats.values() 
                if region.lower() in t.get('region', '').lower()]
    
    def cleanup_stale(self, max_age: int = 3600):
        """Remove threats older than max_age seconds"""
        now = time.time()
        stale = [tid for tid, t in self.active_threats.items() 
                 if now - t.get('last_seen', 0) > max_age]
        for tid in stale:
            self.remove_threat(tid)
        return len(stale)
    
    def get_stats(self) -> dict:
        """Get tracker statistics"""
        return {
            'active_count': len(self.active_threats),
            'history_count': len(self.threat_history),
            'by_type': self._count_by_type()
        }
    
    def _count_by_type(self) -> dict:
        counts = defaultdict(int)
        for t in self.active_threats.values():
            counts[t.get('type', 'unknown')] += 1
        return dict(counts)


# ==================== CHANNEL INTELLIGENCE FUSION ====================

class ChannelIntelligenceFusion:
    """Multi-channel data fusion for threat intelligence"""
    
    def __init__(self):
        self.channel_data: Dict[str, List[dict]] = defaultdict(list)
        self.fused_threats: Dict[str, dict] = {}
        self.channel_reliability: Dict[str, float] = {}
        self.correlation_window = 300  # 5 minutes
        
    def add_channel_report(self, channel: str, report: dict):
        """Add a report from a channel"""
        report['timestamp'] = time.time()
        report['channel'] = channel
        self.channel_data[channel].append(report)
        
        # Cleanup old reports
        cutoff = time.time() - self.correlation_window * 2
        self.channel_data[channel] = [
            r for r in self.channel_data[channel] 
            if r['timestamp'] > cutoff
        ]
        
    def correlate_reports(self) -> List[dict]:
        """Find correlated reports across channels"""
        all_reports = []
        for reports in self.channel_data.values():
            all_reports.extend(reports)
        
        if not all_reports:
            return []
            
        # Group by location/time
        correlated = []
        used = set()
        
        for i, r1 in enumerate(all_reports):
            if i in used:
                continue
                
            group = [r1]
            used.add(i)
            
            for j, r2 in enumerate(all_reports[i+1:], i+1):
                if j in used:
                    continue
                if self._reports_correlate(r1, r2):
                    group.append(r2)
                    used.add(j)
            
            if len(group) > 1:
                correlated.append(self._fuse_reports(group))
                
        return correlated
    
    def _reports_correlate(self, r1: dict, r2: dict) -> bool:
        """Check if two reports likely describe the same threat"""
        # Time proximity
        if abs(r1['timestamp'] - r2['timestamp']) > self.correlation_window:
            return False
            
        # Location proximity
        loc1 = r1.get('location', '')
        loc2 = r2.get('location', '')
        if loc1 and loc2:
            if loc1.lower() == loc2.lower():
                return True
            # Check region match
            reg1 = r1.get('region', '')
            reg2 = r2.get('region', '')
            if reg1 and reg2 and reg1 == reg2:
                return True
                
        return False
    
    def _fuse_reports(self, reports: List[dict]) -> dict:
        """Fuse multiple reports into single assessment"""
        channels = list(set(r['channel'] for r in reports))
        
        # Aggregate confidence based on channel reliability
        total_confidence = 0
        for r in reports:
            ch_reliability = self.channel_reliability.get(r['channel'], 0.7)
            total_confidence += r.get('confidence', 0.7) * ch_reliability
            
        avg_confidence = total_confidence / len(reports)
        
        # Multi-source bonus
        if len(channels) > 1:
            avg_confidence = min(avg_confidence * 1.2, 1.0)
            
        return {
            'location': reports[0].get('location'),
            'region': reports[0].get('region'),
            'type': reports[0].get('type'),
            'confidence': avg_confidence,
            'source_count': len(reports),
            'channels': channels,
            'timestamp': max(r['timestamp'] for r in reports)
        }
    
    def set_channel_reliability(self, channel: str, reliability: float):
        """Set reliability score for a channel (0-1)"""
        self.channel_reliability[channel] = max(0, min(1, reliability))
        
    def get_stats(self) -> dict:
        return {
            'channels': list(self.channel_data.keys()),
            'report_counts': {ch: len(reports) for ch, reports in self.channel_data.items()},
            'fused_threats': len(self.fused_threats)
        }


# ==================== TRAJECTORY BUILDER ====================

class TrajectoryBuilder:
    """Build and predict threat trajectories"""
    
    def __init__(self):
        self.trajectories: Dict[str, List[dict]] = {}
        self.predictions: Dict[str, dict] = {}
        
    def add_point(self, threat_id: str, lat: float, lon: float, timestamp: float = None):
        """Add a point to threat trajectory"""
        if timestamp is None:
            timestamp = time.time()
            
        if threat_id not in self.trajectories:
            self.trajectories[threat_id] = []
            
        self.trajectories[threat_id].append({
            'lat': lat,
            'lon': lon,
            'timestamp': timestamp
        })
        
        # Keep last 50 points
        if len(self.trajectories[threat_id]) > 50:
            self.trajectories[threat_id] = self.trajectories[threat_id][-50:]
            
    def get_trajectory(self, threat_id: str) -> List[dict]:
        """Get trajectory points for a threat"""
        return self.trajectories.get(threat_id, [])
    
    def predict_position(self, threat_id: str, seconds_ahead: int = 300) -> Optional[dict]:
        """Predict future position based on trajectory"""
        points = self.trajectories.get(threat_id, [])
        if len(points) < 2:
            return None
            
        # Use last few points for velocity estimation
        recent = points[-5:] if len(points) >= 5 else points
        
        # Calculate average velocity
        total_dlat = 0
        total_dlon = 0
        total_dt = 0
        
        for i in range(1, len(recent)):
            p1, p2 = recent[i-1], recent[i]
            dt = p2['timestamp'] - p1['timestamp']
            if dt > 0:
                total_dlat += (p2['lat'] - p1['lat']) / dt
                total_dlon += (p2['lon'] - p1['lon']) / dt
                total_dt += 1
                
        if total_dt == 0:
            return None
            
        vlat = total_dlat / total_dt
        vlon = total_dlon / total_dt
        
        last = points[-1]
        predicted_lat = last['lat'] + vlat * seconds_ahead
        predicted_lon = last['lon'] + vlon * seconds_ahead
        
        # Estimate speed in km/h
        speed_kmh = math.sqrt(vlat**2 + vlon**2) * 111 * 3600  # rough conversion
        
        return {
            'lat': predicted_lat,
            'lon': predicted_lon,
            'timestamp': last['timestamp'] + seconds_ahead,
            'confidence': 0.7 if len(points) >= 5 else 0.5,
            'speed_kmh': speed_kmh
        }
    
    def get_heading(self, threat_id: str) -> Optional[float]:
        """Get current heading in degrees (0=N, 90=E)"""
        points = self.trajectories.get(threat_id, [])
        if len(points) < 2:
            return None
            
        p1, p2 = points[-2], points[-1]
        dlat = p2['lat'] - p1['lat']
        dlon = p2['lon'] - p1['lon']
        
        heading = math.degrees(math.atan2(dlon, dlat))
        return (heading + 360) % 360
    
    def cleanup_old(self, max_age: int = 3600):
        """Remove old trajectories"""
        now = time.time()
        stale = []
        for tid, points in self.trajectories.items():
            if not points or now - points[-1]['timestamp'] > max_age:
                stale.append(tid)
        for tid in stale:
            del self.trajectories[tid]
            self.predictions.pop(tid, None)
        return len(stale)


# Global instances
THREAT_TRACKER = ThreatTracker()
CHANNEL_FUSION = ChannelIntelligenceFusion()
TRAJECTORY_BUILDER = TrajectoryBuilder()

# ==================== AI GEOCODING HELPERS ====================

def _get_groq_cache_key(text: str) -> str:
    """Generate cache key for Groq responses"""
    return f"groq_{hash(text[:200])}"

def _groq_rate_limit():
    """Apply rate limiting for Groq API"""
    global _groq_last_call
    now = time.time()
    if now - _groq_last_call < _groq_min_interval:
        time.sleep(_groq_min_interval - (now - _groq_last_call))
    _groq_last_call = time.time()


# AI function stubs - these call Groq API if enabled
async def ai_extract_location(message_text: str) -> Optional[dict]:
    """Use Groq AI to extract location from message - stub, implement in app.py"""
    return None

async def ai_predict_route(threat_type: str, current_region: str, heading: float = None) -> Optional[dict]:
    """Use Groq AI to predict threat route - stub, implement in app.py"""
    return None

async def ai_classify_threat(message_text: str) -> Optional[dict]:
    """Use Groq AI to classify threat type - stub, implement in app.py"""
    return None


def get_ai_systems_stats() -> dict:
    """Get statistics from all AI systems"""
    return {
        'threat_tracker': THREAT_TRACKER.get_stats(),
        'channel_fusion': CHANNEL_FUSION.get_stats(),
        'trajectories': len(TRAJECTORY_BUILDER.trajectories)
    }
