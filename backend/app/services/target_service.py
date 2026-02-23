from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.target import Target
from app.schemas.target import TargetCreate
from fastapi import HTTPException

async def create_target(db: AsyncSession, target_in: TargetCreate) -> Target:
    # 중복 체크
    query = select(Target).where(Target.domain == target_in.domain)
    result = await db.execute(query)
    existing_target = result.scalar_one_or_none()
    
    if existing_target:
        raise HTTPException(status_code=400, detail="Target already exists")
    
    db_target = Target(domain=target_in.domain)
    db.add(db_target)
    await db.commit()
    await db.refresh(db_target)
    return db_target

async def get_targets(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Target]:
    query = select(Target).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_target(db: AsyncSession, target_id: str) -> Target | None:
    query = select(Target).where(Target.id == target_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()
