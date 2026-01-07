import copy
import json
import logging
import os
import shutil
import tempfile
import threading
from typing import Any, Callable, Dict, List, Optional

Message = Dict[str, Any]

log = logging.getLogger(__name__)


class MessageStore:
    """File-backed storage with caching, retention and atomic writes."""

    def __init__(
        self,
        path: str,
        prune_fn: Optional[Callable[[List[Message]], List[Message]]] = None,
        preserve_manual: bool = True,
        backup_count: int = 3,
    ) -> None:
        self.path = path
        self.prune_fn = prune_fn
        self.preserve_manual = preserve_manual
        self.backup_count = max(0, backup_count)
        self._cache: List[Message] = []
        self._cache_mtime: float = 0.0
        self._lock = threading.RLock()

    def load(self) -> List[Message]:
        with self._lock:
            data = self._ensure_cache()
            return copy.deepcopy(data)

    def save(self, data: List[Message]) -> List[Message]:
        with self._lock:
            working = self._apply_retention(copy.deepcopy(data))
            if self.preserve_manual:
                working = self._merge_manual_markers(working)
            self._write_atomic(working)
            self._cache = copy.deepcopy(working)
            self._cache_mtime = self._current_mtime()
            return copy.deepcopy(working)

    # ----- Internal helpers -----
    def _ensure_cache(self) -> List[Message]:
        current_mtime = self._current_mtime()
        if self._cache and current_mtime == self._cache_mtime:
            return self._cache
        self._cache = self._read_from_disk()
        self._cache_mtime = self._current_mtime()
        return self._cache

    def _current_mtime(self) -> float:
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return 0.0

    def _read_from_disk(self) -> List[Message]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as exc:
            # Corrupted file – create backup copy for investigation and reset to empty
            corrupted_path = f"{self.path}.corrupted"
            try:
                shutil.copy2(self.path, corrupted_path)
                log.warning("messages.json corrupted, backup saved to %s", corrupted_path)
            except OSError:
                log.warning("Failed to backup corrupted messages file: %s", exc)
            return []

    def _apply_retention(self, data: List[Message]) -> List[Message]:
        if self.prune_fn:
            try:
                return self.prune_fn(data)
            except Exception:
                return data
        return data

    def _merge_manual_markers(self, data: List[Message]) -> List[Message]:
        existing = self._ensure_cache()
        if not existing:
            return data
        manual_existing = [m for m in existing if m.get("manual")]
        if not manual_existing:
            return data
        data_ids = {m.get("id") for m in data if m.get("id")}
        restored = [m for m in manual_existing if m.get("id") and m.get("id") not in data_ids]
        if restored:
            data.extend(restored)
            log.debug("Restored %d manual markers during save merge", len(restored))
        return data

    def _write_atomic(self, data: List[Message]) -> None:
        base_dir = os.path.dirname(self.path) or "."
        os.makedirs(base_dir, exist_ok=True)
        if os.path.exists(self.path):
            self._rotate_backups()
        temp_file = None
        try:
            temp = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=base_dir,
                suffix=".tmp",
            )
            temp_file = temp.name
            with temp:
                json.dump(data, temp, ensure_ascii=False, indent=2)
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_file, self.path)
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    def _rotate_backups(self) -> None:
        if self.backup_count <= 0:
            return
        for idx in range(self.backup_count, 0, -1):
            src = f"{self.path}.bak{idx - 1}" if idx > 1 else self.path
            dst = f"{self.path}.bak{idx}"
            if os.path.exists(src):
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    continue


def _get_persistent_path(filename: str) -> str:
    """Get the path for persistent storage, using /data on Render if available."""
    persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
    if persistent_dir and os.path.isdir(persistent_dir):
        persistent_path = os.path.join(persistent_dir, filename)
        # Migrate from old location if exists
        if os.path.exists(filename) and not os.path.exists(persistent_path):
            try:
                import shutil
                shutil.copy2(filename, persistent_path)
                log.info(f"Migrated {filename} to {persistent_path}")
            except Exception as e:
                log.warning(f"Failed to migrate {filename}: {e}")
        return persistent_path
    return filename


class DeviceStore:
    """Storage for FCM device tokens and their region preferences."""

    def __init__(self, path: str = None):
        self.path = path if path else _get_persistent_path("devices.json")
        self._lock = threading.RLock()

    def register_device(self, token: str, regions: List[str], device_id: str) -> None:
        """Register or update a device."""
        with self._lock:
            devices = self._load()
            from datetime import datetime
            devices[device_id] = {
                "token": token,
                "regions": regions,
                "enabled": True,
                "last_active": datetime.utcnow().isoformat(),
            }
            self._save(devices)
            log.info(f"Registered device {device_id[:20]}... with {len(regions)} regions")

    def save_device(self, device_id: str, token: str, regions: List[str], enabled: bool = True) -> None:
        """Save or update device information."""
        with self._lock:
            devices = self._load()
            from datetime import datetime
            devices[device_id] = {
                "token": token,
                "regions": regions,
                "enabled": enabled,
                "last_active": datetime.utcnow().isoformat(),
            }
            self._save(devices)
            log.info(f"Saved device {device_id[:20]}... with {len(regions)} regions (enabled={enabled})")

    def update_regions(self, device_id: str, regions: List[str]) -> None:
        """Update regions for an existing device."""
        with self._lock:
            devices = self._load()
            if device_id in devices:
                devices[device_id]["regions"] = regions
                from datetime import datetime
                devices[device_id]["last_active"] = datetime.utcnow().isoformat()
                self._save(devices)
                log.info(f"Updated regions for device {device_id[:20]}...")

    def get_devices_for_region(self, region: str) -> List[Dict[str, Any]]:
        """Get all devices subscribed to a specific region."""
        with self._lock:
            devices = self._load()
            result = []
            for device_id, data in devices.items():
                if not data.get("enabled", True):
                    continue
                if region in data.get("regions", []):
                    result.append({
                        "device_id": device_id,
                        "token": data["token"],
                        "regions": data["regions"],
                    })
            return result

    def remove_device(self, device_id: str) -> None:
        """Remove a device from the store."""
        with self._lock:
            devices = self._load()
            if device_id in devices:
                del devices[device_id]
                self._save(devices)
                log.info(f"Removed device {device_id[:20]}...")

    def clean_inactive_devices(self, days: int = 30) -> int:
        """Remove devices that haven't been active for specified days."""
        with self._lock:
            devices = self._load()
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            to_remove = []
            
            for device_id, data in devices.items():
                last_active_str = data.get("last_active")
                if not last_active_str:
                    to_remove.append(device_id)
                    continue
                try:
                    last_active = datetime.fromisoformat(last_active_str)
                    if last_active < cutoff:
                        to_remove.append(device_id)
                except (ValueError, TypeError):
                    to_remove.append(device_id)
            
            for device_id in to_remove:
                del devices[device_id]
            
            if to_remove:
                self._save(devices)
                log.info(f"Cleaned {len(to_remove)} inactive devices")
            
            return len(to_remove)

    def _load(self) -> Dict[str, Any]:
        """Load devices from disk."""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as exc:
            log.error(f"Failed to load devices: {exc}")
            return {}

    def _save(self, devices: Dict[str, Any]) -> None:
        """Save devices to disk."""
        try:
            with open(self.path, "w", encoding="utf-8") as fp:
                json.dump(devices, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            log.error(f"Failed to save devices: {exc}")

