"""
Alarm monitoring background service.

Фоновий сервіс для моніторингу змін тривог та відправки нотифікацій.
"""
import time
import threading
import logging
from typing import Optional, Callable, List

from services.alarms.client import AlarmClient
from services.alarms.state import AlarmStateManager, StateChange, AlarmChange

log = logging.getLogger(__name__)


class AlarmMonitor:
    """
    Background alarm monitoring service.
    
    Features:
    - Periodic polling of ukrainealarm API
    - State change detection
    - Callback-based notifications
    - Thread-safe operation
    - Graceful shutdown
    """
    
    DEFAULT_POLL_INTERVAL = 30  # seconds
    
    def __init__(
        self,
        client: AlarmClient,
        state_manager: Optional[AlarmStateManager] = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        on_alarm_start: Optional[Callable[[StateChange], None]] = None,
        on_alarm_end: Optional[Callable[[StateChange], None]] = None,
        district_only: bool = True,
    ):
        """
        Args:
            client: AlarmClient for API access
            state_manager: Optional external state manager
            poll_interval: Seconds between API polls
            on_alarm_start: Callback when alarm starts
            on_alarm_end: Callback when alarm ends
            district_only: Only notify for district-level changes
        """
        self._client = client
        self._state = state_manager or AlarmStateManager()
        self._poll_interval = poll_interval
        self._on_start = on_alarm_start
        self._on_end = on_alarm_end
        self._district_only = district_only
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Stats
        self._cycles = 0
        self._last_poll_time: Optional[float] = None
        self._consecutive_failures = 0
    
    def start(self) -> None:
        """Start the monitoring thread."""
        if self._running:
            log.warning("Monitor already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name='AlarmMonitor',
        )
        self._thread.start()
        log.info("AlarmMonitor started")
    
    def stop(self, timeout: float = 5.0) -> None:
        """Stop the monitoring thread."""
        if not self._running:
            return
        
        log.info("Stopping AlarmMonitor...")
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                log.warning("Monitor thread did not stop cleanly")
            self._thread = None
        
        log.info("AlarmMonitor stopped")
    
    def poll_now(self) -> List[StateChange]:
        """
        Manually trigger a poll (synchronous).
        
        Returns:
            List of state changes detected
        """
        return self._do_poll()
    
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running and self._thread is not None and self._thread.is_alive()
    
    def get_state_manager(self) -> AlarmStateManager:
        """Get the state manager."""
        return self._state
    
    def stats(self) -> dict:
        """Get monitor statistics."""
        return {
            'running': self.is_running(),
            'cycles': self._cycles,
            'last_poll': self._last_poll_time,
            'consecutive_failures': self._consecutive_failures,
            'state': self._state.stats(),
            'client': self._client.stats(),
        }
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        log.info("=== ALARM MONITORING LOOP STARTED ===")
        
        while self._running:
            try:
                self._do_poll()
            except Exception as e:
                log.error(f"Monitor poll error: {e}")
                self._consecutive_failures += 1
            
            # Wait for next poll or stop signal
            if self._stop_event.wait(timeout=self._poll_interval):
                break  # Stop was requested
        
        log.info("=== ALARM MONITORING LOOP ENDED ===")
    
    def _do_poll(self) -> List[StateChange]:
        """Execute a single poll cycle."""
        self._cycles += 1
        self._last_poll_time = time.time()
        
        # Fetch alerts from API
        regions, from_cache = self._client.get_alerts()
        
        if not regions and not from_cache:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 5:
                log.error(f"API unavailable for {self._consecutive_failures} cycles")
            return []
        
        self._consecutive_failures = 0
        
        # First run - initialize state without notifications
        if self._state.is_first_run():
            raw_data, _ = self._client.get_alerts_raw()
            self._state.initialize_from_api(raw_data)
            return []
        
        # Get raw data for state update
        raw_data, _ = self._client.get_alerts_raw()
        
        # Update state and get changes
        changes = self._state.update_batch(raw_data)
        
        # Process changes
        for change in changes:
            self._handle_change(change)
        
        return changes
    
    def _handle_change(self, change: StateChange) -> None:
        """Handle a state change."""
        # Filter by region type if needed
        if self._district_only and not change.is_district:
            if change.is_start:
                log.info(f"ℹ️ Oblast alarm started (no push): {change.region_name}")
            return
        
        # Call appropriate callback
        if change.is_start:
            log.info(f"🚨 ALARM STARTED: {change.region_name} ({change.region_type})")
            if self._on_start:
                try:
                    self._on_start(change)
                except Exception as e:
                    log.error(f"Error in on_start callback: {e}")
                    
        elif change.is_end:
            log.info(f"✅ ALARM ENDED: {change.region_name} ({change.region_type})")
            if self._on_end:
                try:
                    self._on_end(change)
                except Exception as e:
                    log.error(f"Error in on_end callback: {e}")
