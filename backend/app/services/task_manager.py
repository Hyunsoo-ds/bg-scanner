import redis.asyncio as redis
from app.config import settings
from app.models.scan import Scan
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from datetime import datetime
import asyncio

class TaskManager:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    async def increment_task_count(self, scan_id: str, count: int = 1):
        """Increase the pending task count for a scan."""
        key = f"scan:{scan_id}:pending_tasks"
        await self.redis.incrby(key, count)
        print(f"[TaskManager] Incremented task count for {scan_id} by {count}")

    async def decrement_task_count(self, scan_id: str):
        """Decrease the pending task count. If zero, mark scan as completed."""
        key = f"scan:{scan_id}:pending_tasks"
        new_value = await self.redis.decr(key)
        print(f"[TaskManager] Decremented task count for {scan_id}. New value: {new_value}")
        
        if new_value <= 0:
            print(f"[TaskManager] Scan {scan_id} finished. Updating status to completed.")
            # Mark scan as completed in DB
            # Create a local engine/session to ensure thread/task safety
            local_engine = create_async_engine(settings.DATABASE_URL, echo=False)
            LocalSession = sessionmaker(bind=local_engine, class_=AsyncSession, expire_on_commit=False)
            
            try:
                async with LocalSession() as db:
                    await db.execute(
                        update(Scan)
                        .where(Scan.id == scan_id)
                        .values(
                            status="completed",
                            phase="Completed",
                            progress_percent=100,
                            finished_at=datetime.utcnow()
                        )
                    )
                    await db.commit()
            except Exception as e:
                print(f"[TaskManager] Database update failed: {e}")
            finally:
                await local_engine.dispose()
            
            # Set expiry for the key just in case
            await self.redis.expire(key, 3600)

task_manager = TaskManager()
