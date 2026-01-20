from __future__ import annotations

import json

from core.message_store import MessageStore


def test_save_and_load_roundtrip(tmp_path):
    target = tmp_path / "messages.json"
    store = MessageStore(str(target))

    payload = [
        {"id": "auto1", "manual": False, "date": "2025-01-01 00:00:00", "lat": 50.0, "lng": 30.0},
        {"id": "manual1", "manual": True, "date": "2025-01-01 00:01:00", "lat": 51.0, "lng": 31.0},
    ]

    saved = store.save(payload)
    assert saved == payload
    loaded = store.load()
    assert loaded == payload
    assert loaded is not payload  # ensure deep copy is returned


def test_manual_markers_restored(tmp_path):
    target = tmp_path / "messages.json"
    existing = [
        {"id": "keep", "manual": True, "date": "2025-01-01 00:00:00", "lat": 1, "lng": 2},
        {"id": "old-auto", "manual": False, "date": "2025-01-01 00:05:00", "lat": 3, "lng": 4},
    ]
    target.write_text(json.dumps(existing, ensure_ascii=False))

    store = MessageStore(str(target))
    new_data = [
        {"id": "new-auto", "manual": False, "date": "2025-01-01 00:10:00", "lat": 5, "lng": 6}
    ]

    result = store.save(new_data)
    manual_ids = {m["id"] for m in result if m.get("manual")}
    assert "keep" in manual_ids


def test_prune_callback_applied(tmp_path):
    recorded = {"called": False}

    def prune(data):
        recorded["called"] = True
        return data[-1:]

    store = MessageStore(str(tmp_path / "messages.json"), prune_fn=prune, preserve_manual=False)
    store.save([
        {"id": "first", "manual": False, "date": "2025-02-01 10:00:00", "lat": 0, "lng": 0},
        {"id": "second", "manual": False, "date": "2025-02-01 10:05:00", "lat": 1, "lng": 1},
    ])

    assert recorded["called"] is True
    assert [m["id"] for m in store.load()] == ["second"]
