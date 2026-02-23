from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.scan import Scan
from app.models.target import Target
from app.schemas.scan import ScanCreate
from app.workers.subdomain_task import run_subdomain_scan
from fastapi import HTTPException
from datetime import datetime

async def create_scan(db: AsyncSession, scan_in: ScanCreate) -> Scan:
    # Target 존재 여부 확인
    result = await db.execute(select(Target).where(Target.id == scan_in.target_id))
    target = result.scalar_one_or_none()
    
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    db_scan = Scan(
        target_id=scan_in.target_id,
        config=scan_in.config,
        status="queued",
        started_at=datetime.utcnow()
    )
    db.add(db_scan)
    await db.commit()
    await db.refresh(db_scan)
    
    # Celery Task 실행 (비동기)
    try:
        run_subdomain_scan.delay(db_scan.id)
    except Exception as e:
        print(f"Error starting celery task: {e}")
        # 실패 처리 로직 추가 가능
    
    return db_scan

async def get_scans(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Scan]:
    query = select(Scan).offset(skip).limit(limit).order_by(Scan.started_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_scan(db: AsyncSession, scan_id: str) -> Scan | None:
    query = select(Scan).where(Scan.id == scan_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()
