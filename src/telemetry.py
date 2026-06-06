import sys
import json
import time
from contextlib import contextmanager

def safe_serialize(details: dict) -> str:
    """Safe serializer that converts non-serializable types (Exception, datetime, set, etc.) to string."""
    sanitized = {}
    for k, v in details.items():
        if isinstance(v, (dict, list, str, int, float, bool, type(None))):
            sanitized[k] = v
        else:
            sanitized[k] = str(v)
    return json.dumps(sanitized)

def log_event(event_name: str, details: dict):
    """Serialize metadata and print directly to sys.stdout to prevent logging conflicts and ensure async delivery on Vercel."""
    payload = {
        "event": event_name,
        "category": "telemetry",
        **details
    }
    # Direct write to sys.stdout ensures pytest capsys captures it correctly
    sys.stdout.write(safe_serialize(payload) + "\n")
    sys.stdout.flush()

@contextmanager
def duration_tracker(event_name: str, context: dict):
    """Context manager measuring execution time in milliseconds and logging trace results."""
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        duration_ms = (end - start) * 1000.0
        details = {
            **context,
            "duration_ms": duration_ms
        }
        log_event(event_name, details)

