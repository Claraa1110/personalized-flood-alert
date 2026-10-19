from fastapi import Request
from slowapi import Limiter


def _get_key(request: Request) -> str:
    device_id = request.headers.get("X-Device-Id", "").strip()
    if device_id:
        return f"device:{device_id}"
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_key)
