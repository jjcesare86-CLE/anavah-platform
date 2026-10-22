import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown"))


def rate_limit(request: Request, bucket: str, limit: int, per_seconds: int):
    """Tiny in-memory limiter (per worker). Good enough for abuse damping on a small site."""
    key = f"{bucket}:{client_ip(request)}"
    now = time.time()
    q = _hits[key]
    while q and q[0] < now - per_seconds:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests. Please wait a moment and try again.")
    q.append(now)
    if len(_hits) > 5000:
        _hits.clear()


def clear_limits():
    _hits.clear()
