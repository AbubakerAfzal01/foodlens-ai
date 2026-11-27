"""Tiny in-memory sliding-window rate limiter (per client IP).

Good enough for a single process. On serverless hosts each instance keeps its
own counter, so treat it as a speed bump, not a hard quota; also set a spending
cap on the Gemini key.
"""
import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_hits = defaultdict(deque)


def allow(key, limit, window=60.0):
    if limit <= 0:
        return True
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        if len(_hits) > 5000:  # keep memory bounded
            for k in [k for k, v in _hits.items() if not v]:
                _hits.pop(k, None)
        return True


def reset():
    with _lock:
        _hits.clear()
