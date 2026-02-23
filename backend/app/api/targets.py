from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.target import TargetCreate, TargetResponse
from app.services import target_service

router = APIRouter()

@router.post("", response_model=TargetResponse)
async def create_target(target: TargetCreate, db: AsyncSession = Depends(get_db)):
    return await target_service.create_target(db, target)

@router.get("", response_model=List[TargetResponse])
async def read_targets(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await target_service.get_targets(db, skip, limit)

@router.get("/{target_id}", response_model=TargetResponse)
async def read_target(target_id: str, db: AsyncSession = Depends(get_db)):
    target = await target_service.get_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return target
