from fastapi import APIRouter, Depends
from app.auth import get_device_id

router = APIRouter()


@router.get("/me")
async def get_me(device_id: str = Depends(get_device_id)):
    return {"device_id": device_id}
