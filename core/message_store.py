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
