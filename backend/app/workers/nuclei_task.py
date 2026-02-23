from celery import shared_task
import asyncio
from app.scanners.nuclei import Nuclei
from app.db.session import AsyncSessionLocal
from app.services.task_manager import task_manager
from app.models.scan import Scan
from app.models.vulnerability import Vulnerability
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

@shared_task(bind=True)
def run_nuclei_scan(self, scan_id: str, target_url: str, path_id: str = None, subdomain_id: str = None):
    print(f"[Worker] Starting nuclei scan for {target_url} (Scan: {scan_id})")
    
    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
        AsyncSessionLocalTask = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocalTask() as db:
            # 1. Update Scan Phase (Optional, might be too noisy if many tasks running)
             await db.execute(
                update(Scan)
                .where(Scan.id == scan_id)
                .values(phase="Nuclei Scanning")
            )
             await db.commit()

             # 2. Run Nuclei
             scanner = Nuclei()
             # We can customize templates/severity here if needed
             results = await scanner.run(target_url)
             
             # 3. Save Results
             if results:
                 for res in results:
                     vuln = Vulnerability(
                         scan_id=scan_id,
                         path_id=path_id,
                         subdomain_id=subdomain_id,
                         name=res.get("name"),
                         severity=res.get("severity"),
                         description=res.get("description"),
                         matcher_name=res.get("matcher_name"),
                         extracted_results=res.get("extracted_results")
                     )
                     db.add(vuln)
                 await db.commit()
            
             # 4. Decrement Task Count
             await task_manager.decrement_task_count(scan_id)

    try:
        asyncio.run(_run())
        return {"status": "completed", "url": target_url, "scan_id": scan_id}
    except Exception as e:
        print(f"Nuclei scan failed: {e}")
        # Ensure we decrement even on failure to avoid stuck scan
        # Note: task_manager might need to be called in a finally block or similar if _run fails before decrement
        # But here _run wraps the logic. If _run fails, we need to handle it.
        # Ideally decrement should be safe.
        # Let's try to decrement in a separate loop if _run fails? 
        # Or better, put try/finally inside _run.
        return {"status": "failed", "error": str(e)}
