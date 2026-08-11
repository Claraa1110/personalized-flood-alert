from fastapi import Header, HTTPException


async def get_device_id(
    x_device_id: str | None = Header(None, alias="X-Device-Id"),
) -> str:
    if not x_device_id or not x_device_id.strip():
        raise HTTPException(status_code=400, detail="X-Device-Id header is required")
    return x_device_id.strip()
