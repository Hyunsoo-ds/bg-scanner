import asyncio
from celery import shared_task
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.technology import Technology
from app.models.subdomain import Subdomain
from app.models.scan import Scan
from app.services.task_manager import task_manager
from sqlalchemy import update
from app.scanners.webanalyze import WebanalyzeScanner

@shared_task(name="app.workers.tech_task.run_tech_scan", bind=True)
def run_tech_scan(self, subdomain_id: str, url: str):
    """
    Simulates async execution for Celery using asyncio.run
    """
    asyncio.run(_run(subdomain_id, url))

async def _run(subdomain_id: str, url: str):
    print(f"Starting Tech Profilling for: {url}")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    AsyncSessionLocalTask = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    scan_id = None
    
    # 1. Update Status (Running)
    async with AsyncSessionLocalTask() as db:
        res_sub = await db.execute(select(Subdomain).where(Subdomain.id == subdomain_id))
        subdomain = res_sub.scalar_one_or_none()
        
        if not subdomain:
            print(f"Subdomain {subdomain_id} not found.")
            await engine.dispose()
            return

        scan_id = subdomain.scan_id
        
        # Update Phase & Status
        await db.execute(update(Scan).where(Scan.id == scan_id).values(phase="Tech Profiling"))
        await db.execute(update(Subdomain).where(Subdomain.id == subdomain_id).values(task_status="Tech Profiling"))
        await db.commit()

    # 2. Scanner Execution
    scanner = WebanalyzeScanner(url)
    results = await scanner.run()
    
    if not results:
        print("No technologies found.")
        # Mark as Profiled anyway
        async with AsyncSessionLocalTask() as db:
             await db.execute(update(Subdomain).where(Subdomain.id == subdomain_id).values(task_status="Tech Profiled"))
             await db.commit()
             await task_manager.decrement_task_count(scan_id)
        
        await engine.dispose()
        return

    # 3. Save Results
    async with AsyncSessionLocalTask() as db:
        for tech in results:
             new_tech = Technology(
                 subdomain_id=subdomain_id,
                 name=tech.get('app_name', 'Unknown'),
                 version=tech.get('version'),
                 categories=tech.get('categories', [])
             )
             db.add(new_tech)
        
        await db.execute(update(Subdomain).where(Subdomain.id == subdomain_id).values(task_status="Tech Profiled"))
        await db.commit()
        
        await task_manager.decrement_task_count(scan_id)
    
    await engine.dispose()
    print(f"Saved {len(results)} technologies for {url}")
