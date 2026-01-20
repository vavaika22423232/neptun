"""
Alarm state management.

Thread-safe стан тривог з відстеженням змін.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

log = logging.getLogger(__name__)


class AlarmChange(Enum):
    """Type of alarm state change."""
    STARTED = 'started'
    ENDED = 'ended'
    TYPE_CHANGED = 'type_changed'
    NO_CHANGE = 'no_change'


@dataclass
class RegionAlarmState:
    """State of alarm for a single region."""
    region_id: str
    region_name: str
    region_type: str  # State, District, Community
    active: bool = False
    alert_types: list[str] = field(default_factory=list)
    last_changed: float = field(default_factory=time.time)
    notified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            'region_id': self.region_id,
            'region_name': self.region_name,
            'region_type': self.region_type,
            'active': self.active,
            'alert_types': self.alert_types,
            'last_changed': self.last_changed,
            'notified': self.notified,
        }


@dataclass
class StateChange:
    """Represents a state change event."""
    region_id: str
    region_name: str
    region_type: str
    change_type: AlarmChange
    alert_types: list[str]
    timestamp: float

    @property
    def is_start(self) -> bool:
        return self.change_type == AlarmChange.STARTED

    @property
    def is_end(self) -> bool:
        return self.change_type == AlarmChange.ENDED

    @property
    def is_district(self) -> bool:
        return self.region_type == 'District'

    @property
    def is_oblast(self) -> bool:
        return self.region_type == 'State'


class AlarmStateManager:
    """
    Thread-safe alarm state manager.

    Tracks alarm state for all regions and detects changes.
    """

    def __init__(self):
        self._states: dict[str, RegionAlarmState] = {}
        self._lock = threading.RLock()
        self._first_run = True

        # Stats
        self._total_changes = 0
        self._started_count = 0
        self._ended_count = 0

    def update(
        self,
        region_id: str,
        region_name: str,
        region_type: str,
        has_alarm: bool,
        alert_types: list[str],
    ) -> StateChange:
        """
        Update state for a region.

        Args:
            region_id: Unique region identifier
            region_name: Human-readable name
            region_type: State/District/Community
            has_alarm: Whether alarm is currently active
            alert_types: List of active alert types

        Returns:
            StateChange describing what changed
        """
        with self._lock:
            now = time.time()

            # Get or create state
            prev = self._states.get(region_id)
            was_active = prev.active if prev else False

            # Determine change type
            if has_alarm and not was_active:
                change_type = AlarmChange.STARTED
                self._started_count += 1
                self._total_changes += 1
            elif not has_alarm and was_active:
                change_type = AlarmChange.ENDED
                self._ended_count += 1
                self._total_changes += 1
            elif has_alarm and prev and set(alert_types) != set(prev.alert_types):
                change_type = AlarmChange.TYPE_CHANGED
            else:
                change_type = AlarmChange.NO_CHANGE

            # Update state
            self._states[region_id] = RegionAlarmState(
                region_id=region_id,
                region_name=region_name,
                region_type=region_type,
                active=has_alarm,
                alert_types=alert_types,
                last_changed=now if change_type != AlarmChange.NO_CHANGE else (prev.last_changed if prev else now),
                notified=change_type != AlarmChange.NO_CHANGE,
            )

            return StateChange(
                region_id=region_id,
                region_name=region_name,
                region_type=region_type,
                change_type=change_type,
                alert_types=alert_types,
                timestamp=now,
            )

    def update_batch(
        self,
        regions: list[dict[str, Any]],
    ) -> list[StateChange]:
        """
        Update state for multiple regions at once.

        Args:
            regions: List of region dicts from API

        Returns:
            List of StateChanges (only actual changes)
        """
        changes = []
        current_ids: set[str] = set()

        # Process active regions
        for region in regions:
            region_id = region.get('regionId', '')
            if not region_id:
                continue

            current_ids.add(region_id)
            active_alerts = region.get('activeAlerts', [])

            change = self.update(
                region_id=region_id,
                region_name=region.get('regionName', ''),
                region_type=region.get('regionType', ''),
                has_alarm=len(active_alerts) > 0,
                alert_types=[a.get('type', '') for a in active_alerts],
            )

            if change.change_type != AlarmChange.NO_CHANGE:
                changes.append(change)

        # Check for regions that ended (not in current data)
        with self._lock:
            for region_id, state in list(self._states.items()):
                if region_id not in current_ids and state.active:
                    change = self.update(
                        region_id=region_id,
                        region_name=state.region_name,
                        region_type=state.region_type,
                        has_alarm=False,
                        alert_types=[],
                    )
                    if change.change_type != AlarmChange.NO_CHANGE:
                        changes.append(change)

        return changes

    def initialize_from_api(self, regions: list[dict[str, Any]]) -> int:
        """
        Initialize state from API without generating changes.

        Use on first run to prevent notification spam after restart.

        Returns:
            Count of active alarms stored
        """
        with self._lock:
            if not self._first_run:
                return 0

            count = 0
            for region in regions:
                region_id = region.get('regionId', '')
                if not region_id:
                    continue

                active_alerts = region.get('activeAlerts', [])
                has_alarm = len(active_alerts) > 0

                if has_alarm:
                    count += 1
                    self._states[region_id] = RegionAlarmState(
                        region_id=region_id,
                        region_name=region.get('regionName', ''),
                        region_type=region.get('regionType', ''),
                        active=True,
                        alert_types=[a.get('type', '') for a in active_alerts],
                        notified=True,  # Mark as notified to prevent duplicate
                    )

            self._first_run = False
            log.info(f"Initialized alarm state with {count} active alarms")
            return count

    def get_state(self, region_id: str) -> Optional[RegionAlarmState]:
        """Get state for a specific region."""
        with self._lock:
            return self._states.get(region_id)

    def get_active_regions(self) -> list[RegionAlarmState]:
        """Get all regions with active alarms."""
        with self._lock:
            return [s for s in self._states.values() if s.active]

    def get_active_count(self) -> int:
        """Get count of active alarms."""
        with self._lock:
            return sum(1 for s in self._states.values() if s.active)

    def get_active_ids(self) -> set[str]:
        """Get IDs of all regions with active alarms."""
        with self._lock:
            return {s.region_id for s in self._states.values() if s.active}

    def is_first_run(self) -> bool:
        """Check if this is first run (no state loaded yet)."""
        with self._lock:
            return self._first_run

    def stats(self) -> dict[str, Any]:
        """Get state statistics."""
        with self._lock:
            return {
                'total_regions': len(self._states),
                'active_alarms': self.get_active_count(),
                'total_changes': self._total_changes,
                'started_count': self._started_count,
                'ended_count': self._ended_count,
                'first_run': self._first_run,
            }

    def clear(self) -> None:
        """Clear all state."""
        with self._lock:
            self._states.clear()
            self._first_run = True
