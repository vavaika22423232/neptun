from importlib import import_module

import pytest


def test_region_to_region_marker_stays_at_source():
    app = import_module("app")
    message = "Запоріжжя: БпЛА на запоріжжі курсом на Дніпропетровщину"
    result = app.process_message(message, mid=123, date_str="2024-11-20 10:00:00", channel="test")

    assert result, "process_message should return at least one track"
    entry = result[0]

    assert entry["source_match"] == "singleline_region_course"
    assert entry["course_target"] == "Дніпропетровщина"
    assert "trajectory" in entry and entry["trajectory"], "trajectory data must be present"

    zap_lat, zap_lng = app.CITY_COORDS["запоріжжя"]
    assert pytest.approx(entry["lat"], rel=0, abs=0.01) == zap_lat
    assert pytest.approx(entry["lng"], rel=0, abs=0.01) == zap_lng

    traj_start = entry["trajectory"]["start"]
    assert pytest.approx(traj_start[0], rel=0, abs=0.01) == zap_lat
    assert pytest.approx(traj_start[1], rel=0, abs=0.01) == zap_lng
