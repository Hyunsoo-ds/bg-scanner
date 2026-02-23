from celery import shared_task
import asyncio
from app.scanners.subfinder import Subfinder
from app.db.session import AsyncSessionLocal
from app.services import subdomain_service
from app.models.scan import Scan
from app.services.task_manager import task_manager
from app.models.target import Target
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from datetime import datetime

# Celery Task는 동기 함수여야 함 (asyncio.run으로 비동기 코드 실행)
@shared_task(bind=True)
def run_subdomain_scan(self, scan_id: str):
    print(f"[Worker] Starting subdomain scan for {scan_id}")
    
    async def _run():
        # Create a NEW engine for this task to avoid sharing event loops
        # Celery Worker는 각각 별도의 프로세스/스레드일 수 있으므로 
        # 엔진을 여기서 생성해서 쓰는 게 안전할 수 있음 (특히 asyncpg)
        
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
        AsyncSessionLocalTask = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocalTask() as db:
            # 1. 스캔 상태 업데이트 (Running)
            await db.execute(
                update(Scan)
                .where(Scan.id == scan_id)
                .values(status="running", phase="Subdomain Enumeration", progress_percent=10)
            )
            await db.commit()
            
            # 2. 타겟 도메인 가져오기
            result = await db.execute(select(Scan).where(Scan.id == scan_id))
            scan = result.scalar_one_or_none()
            if not scan:
                print(f"Scan {scan_id} not found")
                return

            # Target 정보 가져오기 (Lazy loading 이슈 방지 위해 join 하거나 다시 조회)
            # 여기서는 scan.target_id로 Target 조회는 생략하고, scan.target이 로드되었다고 가정하거나
            # config에 target_domain을 넣는 게 나음. 
            # 일단 Target 조회
            res_target = await db.execute(select(Target).where(Target.id == scan.target_id))
            target = res_target.scalar_one_or_none()
            
            if not target:
                print(f"Target for scan {scan_id} not found")
                return

            # 3. Subfinder 실행
            scanner = Subfinder()
            results = await scanner.run(target.domain)
            # 4. 결과 저장
            # Subfinder가 루트 도메인을 포함하지 않을 수 있으므로, 명시적으로 추가
            root_domain_exists = any(r.get("hostname") == target.domain for r in results)
            if not root_domain_exists:
                results.append({
                    "hostname": target.domain,
                    "ip_address": None, # 나중에 Port Scan 등에서 채워질 수 있음
                    "source": "root_domain"
                })
                
            saved_count = await subdomain_service.save_subdomains(db, scan_id, results)
            
            # 5. Port Scan 트리거 제거 (Manual Mode)
            # subdomains_res = await db.execute(select(Subdomain).where(Subdomain.scan_id == scan_id))
            # subdomains = subdomains_res.scalars().all()
            
            # from app.workers.port_task import run_port_scan
            # for sub in subdomains:
            #     # 비동기적으로 Celery 태스크 호출 (.delay())
            #     run_port_scan.delay(sub.id)
            
            # 6. 스캔 완료 처리 (Task Count Decrement)
            # await db.execute(update(Scan)...) # 완료 처리는 TaskManager가 담당
            await db.execute(
                update(Scan)
                .where(Scan.id == scan_id)
                .values(phase="Subdomain Enumeration Completed")
            )
            await db.commit()
            
            await task_manager.decrement_task_count(scan_id)

    try:
        asyncio.run(_run())
        return {"status": "completed", "scan_id": scan_id}
    except Exception as e:
        print(f"Scan failed: {e}")
        # 실패 상태 업데이트 로직 필요
        return {"status": "failed", "error": str(e)}
