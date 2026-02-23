from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models.subdomain import Subdomain
from app.models.scan import Scan
from app.services.task_manager import task_manager
from sqlalchemy import update
from app.scanners.nmap import NmapScanner
from app.services import port_service
from app.workers.celery_app import celery_app
import asyncio

@shared_task(bind=True)
def run_port_scan(self, subdomain_id: str):
    print(f"[Worker] Starting port scan for subdomain {subdomain_id}")
    
    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
        AsyncSessionLocalTask = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocalTask() as db:
            # 1. 서브도메인 정보 가져오기 (IP 또는 Hostname)
            result = await db.execute(select(Subdomain).where(Subdomain.id == subdomain_id))
            subdomain = result.scalar_one_or_none()
            
            if not subdomain:
                print(f"Subdomain {subdomain_id} not found")
                # Cannot decrement without scan_id, but here we don't know scan_id easily unless we query it. 
                # But wait, we query subdomain to get it. If not found, we can't do anything.
                # Assuming this case is rare or impossible if logic is correct.
                return

            # Update Phase
            await db.execute(
                update(Scan)
                .where(Scan.id == subdomain.scan_id)
                .values(phase="Port Scanning")
            )
            # Update Subdomain Task Status (Running)
            await db.execute(
                update(Subdomain)
                .where(Subdomain.id == subdomain_id)
                .values(task_status="Port Scanning")
            )
            await db.commit()

            target = subdomain.ip_address if subdomain.ip_address else subdomain.hostname
            if not target:
                print(f"No target (IP/Hostname) for subdomain {subdomain_id}")
                await task_manager.decrement_task_count(subdomain.scan_id)
                return

            # 2. Nmap 실행
            scanner = NmapScanner()
            # 타임아웃이나 옵션 등을 config에서 가져올 수도 있음
            ports = await scanner.run(target)
            print(f"Found {len(ports)} ports for {target}")
            
            # 3. 결과 저장
            await port_service.save_ports(db, subdomain_id, ports)
            
            # 4. Tech Profile Trigger (Manual Mode - Removed Automatic Trigger)
            # 5. 후속 스캔 트리거 제거 (Manual Mode)
            pass
            
            # TODO: Vulnerability Scan 트리거 (Phase 2 후반부)
            # Update Subdomain Task Status (Completed)
            await db.execute(
                update(Subdomain)
                .where(Subdomain.id == subdomain_id)
                .values(task_status="Port Scanned")
            )
            await db.commit()
            
            await task_manager.decrement_task_count(subdomain.scan_id) # Decrement for port scan completion

    try:
        asyncio.run(_run())
        return {"status": "completed", "subdomain_id": subdomain_id}
    except Exception as e:
        print(f"Port scan failed: {e}")
        return {"status": "failed", "error": str(e)}
