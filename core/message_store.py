import copy
import json
import logging
import os
import shutil
import tempfile
import threading
from typing import Any, Callable, Optional

Message = dict[str, Any]

log = logging.getLogger(__name__)


class MessageStore:
    """File-backed storage with caching, retention and atomic writes."""

    def __init__(
        self,
        path: str,
        prune_fn: Optional[Callable[[list[Message]], list[Message]]] = None,
        preserve_manual: bool = True,
        backup_count: int = 3,
    ) -> None:
        self.path = path
        self.prune_fn = prune_fn
        self.preserve_manual = preserve_manual
        self.backup_count = max(0, backup_count)
        self._cache: list[Message] = []
        self._cache_mtime: float = 0.0
        self._lock = threading.RLock()

    def load(self) -> list[Message]:
        with self._lock:
            data = self._ensure_cache()
            return copy.deepcopy(data)

    def save(self, data: list[Message]) -> list[Message]:
        with self._lock:
            working = self._apply_retention(copy.deepcopy(data))
            if self.preserve_manual:
                working = self._merge_manual_markers(working)
            self._write_atomic(working)
            self._cache = copy.deepcopy(working)
            self._cache_mtime = self._current_mtime()
            return copy.deepcopy(working)

    # ----- Internal helpers -----
    def _ensure_cache(self) -> list[Message]:
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

    def _read_from_disk(self) -> list[Message]:
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

    def _apply_retention(self, data: list[Message]) -> list[Message]:
        if self.prune_fn:
            try:
                return self.prune_fn(data)
            except Exception:
                return data
        return data

    def _merge_manual_markers(self, data: list[Message]) -> list[Message]:
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

    def _write_atomic(self, data: list[Message]) -> None:
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

    def register_device(self, token: str, regions: list[str], device_id: str) -> None:
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

    def save_device(self, device_id: str, token: str, regions: list[str], enabled: bool = True) -> None:
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

    def update_regions(self, device_id: str, regions: list[str]) -> None:
        """Update regions for an existing device."""
        with self._lock:
            devices = self._load()
            if device_id in devices:
                devices[device_id]["regions"] = regions
                from datetime import datetime
                devices[device_id]["last_active"] = datetime.utcnow().isoformat()
                self._save(devices)
                log.info(f"Updated regions for device {device_id[:20]}...")

    def _normalize_region(self, region: str) -> str:
        """Normalize region name for matching."""
        # Remove common prefixes and suffixes
        normalized = region.lower().strip()
        # Remove oblast suffixes
        for suffix in [' область', ' обл.', ' обл', ' область.']:
            normalized = normalized.replace(suffix, '')
        # Remove district markers
        for suffix in [' район', ' р-н']:
            if suffix in normalized:
                # Extract oblast from "(Xобл.)" if present
                import re
                oblast_match = re.search(r'\(([^)]+обл[^)]*)\)', normalized)
                if oblast_match:
                    normalized = oblast_match.group(1).replace(' обл.', '').replace(' обл', '').strip()
                else:
                    normalized = normalized.split(suffix)[0].strip()
        # Remove city/town info, keep oblast
        import re
        oblast_match = re.search(r'\(([^)]+обл[^)]*)\)', normalized)
        if oblast_match:
            normalized = oblast_match.group(1).replace(' обл.', '').replace(' обл', '').strip()
        return normalized.strip()

    def _regions_match(self, region1: str, region2: str) -> bool:
        """Check if two regions match (fuzzy matching)."""
        n1 = self._normalize_region(region1)
        n2 = self._normalize_region(region2)
        # Direct match
        if n1 == n2:
            return True
        # One contains the other
        if n1 in n2 or n2 in n1:
            return True
        # Check if any word matches (for cases like "Київ" vs "Київська")
        words1 = set(n1.split())
        words2 = set(n2.split())
        # Check root matches (e.g., "київ" matches "київськ")
        for w1 in words1:
            for w2 in words2:
                if len(w1) > 3 and len(w2) > 3:
                    if w1[:4] == w2[:4]:  # First 4 chars match
                        return True
        return False

    def get_devices_for_region(self, region: str) -> list[dict[str, Any]]:
        """Get all devices subscribed to a specific region (with fuzzy matching)."""
        with self._lock:
            devices = self._load()
            result = []
            for device_id, data in devices.items():
                if not data.get("enabled", True):
                    continue
                # Check if any subscribed region matches the alert region
                for subscribed_region in data.get("regions", []):
                    if self._regions_match(region, subscribed_region):
                        result.append({
                            "device_id": device_id,
                            "token": data["token"],
                            "regions": data["regions"],
                        })
                        break  # Don't add same device twice
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

    def _load(self) -> dict[str, Any]:
        """Load devices from disk."""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as fp:
                return json.load(fp)
        except Exception as exc:
            log.error(f"Failed to load devices: {exc}")
            return {}

    def _save(self, devices: dict[str, Any]) -> None:
        """Save devices to disk."""
        try:
            with open(self.path, "w", encoding="utf-8") as fp:
                json.dump(devices, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            log.error(f"Failed to save devices: {exc}")


class FamilyStore:
    """Storage for family safety data with FCM tokens for SOS notifications."""

    def __init__(self, path: str = None):
        self.path = path if path else _get_persistent_path("family_status.json")
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        """Load family data from disk."""
        if not os.path.exists(self.path):
            return {"statuses": {}, "members": {}}
        try:
            with open(self.path, encoding="utf-8") as fp:
                data = json.load(fp)
                # Ensure structure
                if "statuses" not in data:
                    data["statuses"] = {}
                if "members" not in data:
                    data["members"] = {}
                return data
        except Exception as exc:
            log.error(f"Failed to load family data: {exc}")
            return {"statuses": {}, "members": {}}

    def _save(self, data: dict[str, Any]) -> None:
        """Save family data to disk."""
        try:
            with open(self.path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            log.error(f"Failed to save family data: {exc}")

    def get_status(self, code: str) -> Optional[dict[str, Any]]:
        """Get status for a single family code."""
        with self._lock:
            data = self._load()
            return data["statuses"].get(code.upper())

    def get_statuses(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        """Get statuses for multiple family codes."""
        with self._lock:
            data = self._load()
            result = {}
            for code in codes:
                code_upper = code.upper()
                if code_upper in data["statuses"]:
                    result[code_upper] = data["statuses"][code_upper]
                else:
                    result[code_upper] = {"is_safe": False, "last_update": None}
            return result

    def update_status(self, code: str, is_safe: bool, name: str = "", fcm_token: str = None, device_id: str = None) -> None:
        """Update status for a family member."""
        from datetime import datetime
        with self._lock:
            data = self._load()
            code_upper = code.upper()

            # Update status
            data["statuses"][code_upper] = {
                "is_safe": is_safe,
                "last_update": datetime.utcnow().isoformat(),
                "name": name,
            }

            # Store FCM token if provided (for SOS notifications)
            if fcm_token or device_id:
                if code_upper not in data["members"]:
                    data["members"][code_upper] = {}
                if fcm_token:
                    data["members"][code_upper]["fcm_token"] = fcm_token
                if device_id:
                    data["members"][code_upper]["device_id"] = device_id
                data["members"][code_upper]["last_active"] = datetime.utcnow().isoformat()

            self._save(data)
            log.info(f"Updated family status: {code_upper} -> is_safe={is_safe}")

    def send_sos(self, sender_code: str, family_codes: list[str]) -> dict[str, Any]:
        """Mark sender as needing help and return FCM tokens of family members."""
        from datetime import datetime
        with self._lock:
            data = self._load()
            sender_upper = sender_code.upper()

            # Mark sender as NOT safe with SOS flag
            data["statuses"][sender_upper] = {
                "is_safe": False,
                "last_update": datetime.utcnow().isoformat(),
                "sos": True,
                "sos_time": datetime.utcnow().isoformat(),
            }

            # Get FCM tokens for family members
            tokens_to_notify = []
            for code in family_codes:
                code_upper = code.upper()
                if code_upper in data["members"]:
                    member = data["members"][code_upper]
                    if member.get("fcm_token"):
                        tokens_to_notify.append({
                            "code": code_upper,
                            "fcm_token": member["fcm_token"],
                            "device_id": member.get("device_id"),
                        })

            self._save(data)
            log.warning(f"🆘 SOS from {sender_upper} to {len(family_codes)} family members, {len(tokens_to_notify)} have FCM tokens")

            return {
                "sender_code": sender_upper,
                "family_codes": family_codes,
                "tokens_to_notify": tokens_to_notify,
            }

    def clear_sos(self, code: str) -> None:
        """Clear SOS status for a family member."""
        with self._lock:
            data = self._load()
            code_upper = code.upper()
            if code_upper in data["statuses"] and data["statuses"][code_upper].get("sos"):
                del data["statuses"][code_upper]["sos"]
                del data["statuses"][code_upper]["sos_time"]
                self._save(data)
                log.info(f"Cleared SOS for {code_upper}")

    def register_fcm_token(self, code: str, fcm_token: str, device_id: str = None) -> None:
        """Register FCM token for a family member (for receiving SOS notifications)."""
        from datetime import datetime
        with self._lock:
            data = self._load()
            code_upper = code.upper()

            if code_upper not in data["members"]:
                data["members"][code_upper] = {}

            data["members"][code_upper]["fcm_token"] = fcm_token
            if device_id:
                data["members"][code_upper]["device_id"] = device_id
            data["members"][code_upper]["last_active"] = datetime.utcnow().isoformat()

            self._save(data)
            log.info(f"Registered FCM token for family code {code_upper}")


