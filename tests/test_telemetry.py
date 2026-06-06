import json
import logging
import pytest
from unittest.mock import patch, MagicMock
from src.telemetry import safe_serialize, log_event, duration_tracker

def test_safe_serialize_basic_types():
    data = {
        "string": "hello",
        "int": 42,
        "float": 3.14,
        "bool": True,
        "none": None,
        "list": [1, 2, 3],
        "dict": {"a": 1}
    }
    result_str = safe_serialize(data)
    result = json.loads(result_str)
    assert result == data

def test_safe_serialize_complex_types():
    import datetime
    dt = datetime.datetime(2026, 6, 5, 0, 0, 0)
    exc = ValueError("Something went wrong")
    data = {
        "datetime": dt,
        "exception": exc,
        "set": {1, 2, 3}
    }
    result_str = safe_serialize(data)
    result = json.loads(result_str)
    assert result["datetime"] == str(dt)
    assert result["exception"] == str(exc)
    assert result["set"] == str({1, 2, 3})

def test_log_event_writes_json_to_stdout(capsys):
    details = {"key": "value", "number": 123}
    log_event("test_event", details)
    
    captured = capsys.readouterr()
    log_line = captured.out.strip()
    assert log_line != ""
    
    data = json.loads(log_line)
    assert data["event"] == "test_event"
    assert data["category"] == "telemetry"
    assert data["key"] == "value"
    assert data["number"] == 123

def test_duration_tracker_logs_event_with_time(capsys):
    import time
    with duration_tracker("test_duration", {"extra_info": "context"}):
        time.sleep(0.01)
        
    captured = capsys.readouterr()
    log_line = captured.out.strip()
    assert log_line != ""
    
    data = json.loads(log_line)
    assert data["event"] == "test_duration"
    assert data["category"] == "telemetry"
    assert data["extra_info"] == "context"
    assert "duration_ms" in data
    assert data["duration_ms"] >= 10.0

