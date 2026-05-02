from uuid import UUID, uuid4
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

db: dict[UUID, dict] = {}


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float


class ItemResponse(ItemCreate):
    id: UUID


@router.get("/items", response_model=list[ItemResponse])
def list_items():
    return [ItemResponse(id=k, **v) for k, v in db.items()]


@router.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    item_id = uuid4()
    db[item_id] = item.model_dump()
    return ItemResponse(id=item_id, **db[item_id])


@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: UUID):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(id=item_id, **db[item_id])


@router.put("/items/{item_id}", response_model=ItemResponse)
def update_item(item_id: UUID, item: ItemCreate):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    db[item_id] = item.model_dump()
    return ItemResponse(id=item_id, **db[item_id])


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: UUID):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")
    del db[item_id]
