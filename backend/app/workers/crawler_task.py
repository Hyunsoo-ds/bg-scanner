import asyncio
import httpx
from asyncio import Semaphore
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.subdomain import Subdomain
from app.models.scan import Scan
from app.services.task_manager import task_manager
from sqlalchemy import update
from app.scanners.katana import KatanaScanner
from app.scanners.dirsearch import DirsearchScanner
from app.scanners.waybackurls import WaybackurlsScanner
from app.scanners.gau import GauScanner
from app.scanners.result_merger import PathMerger
from app.services import path_service


@shared_task(name="app.workers.crawler_task.run_path_crawl", bind=True)
def run_path_crawl(self, subdomain_id: str, url: str):
    """
    Path Crawling Celery 태스크.
    4개 도구(Katana, dirsearch, waybackurls, gau)를 병렬 실행하고
    결과를 병합·중복 제거 후 DB에 저장합니다.

    Args:
        subdomain_id: 대상 서브도메인 UUID
        url: 크롤링할 URL (예: https://example.com)
    """
    print(f"[CrawlerTask] Starting path crawl for {url} (subdomain: {subdomain_id})")
    asyncio.run(_run(subdomain_id, url))


async def probe_urls(urls_to_probe: list[str]) -> dict[str, dict]:
    """
    httpx를 사용해 URL의 상태 코드와 메타데이터를 확인합니다.
    """
    results = {}
    sem = Semaphore(20) # 동시성 제한
    
    async def fetch(url):
        async with sem:
            try:
                # verify=False로 SSL 오류 무시, timeout 설정
                async with httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True) as client:
                    try:
                        resp = await client.head(url)
                        # 405 Method Not Allowed 등의 경우 GET 시도
                        if resp.status_code >= 400:
                            resp = await client.get(url)
                    except httpx.RequestError:
                         # HEAD 실패 시 GET 시도
                         resp = await client.get(url)

                    results[url] = {
                        "status_code": resp.status_code,
                        "content_type": resp.headers.get("content-type"),
                        "content_length": int(resp.headers.get("content-length") or 0) or None,
                    }
            except Exception as e:
                # 연결 실패 등
                # print(f"[CrawlerTask] Probe failed for {url}: {e}")
                results[url] = {"status_code": None}

    if urls_to_probe:
        await asyncio.gather(*[fetch(u) for u in urls_to_probe])
    return results


async def _run(subdomain_id: str, url: str):
    # 1. 서브도메인 존재 확인
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocalTask = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocalTask() as db:
        res_sub = await db.execute(select(Subdomain).where(Subdomain.id == subdomain_id))
        subdomain = res_sub.scalar_one_or_none()
        if not subdomain:
            print(f"[CrawlerTask] Subdomain {subdomain_id} not found, skipping.")
            await engine.dispose()
            return

        # Update Phase
        await db.execute(
            update(Scan)
            .where(Scan.id == subdomain.scan_id)
            .values(phase="Path Crawling")
        )
        
        # Update Subdomain Task Status (Running)
        await db.execute(
            update(Subdomain)
            .where(Subdomain.id == subdomain_id)
            .values(task_status="Path Crawling")
        )
        
        await db.commit()

    # 2. 4개 스캐너 병렬 실행
    katana = KatanaScanner()
    # dirsearch = DirsearchScanner()
    # waybackurls = WaybackurlsScanner()
    # gau = GauScanner()

    print(f"[CrawlerTask] Running Katana scanner for {url}")
    results_list = await asyncio.gather(
        katana.run(url),
        # dirsearch.run(url),
        # waybackurls.run(url),
        # gau.run(url),
        return_exceptions=True,
    )

    # 예외 처리: 실패한 도구는 빈 리스트로 대체
    cleaned_results = []
    tool_names = ["katana"] #, "dirsearch", "waybackurls", "gau"]
    for i, result in enumerate(results_list):
        if isinstance(result, Exception):
            print(f"[CrawlerTask] {tool_names[i]} failed: {result}")
            cleaned_results.append([])
        else:
            print(f"[CrawlerTask] {tool_names[i]} found {len(result)} URLs")
            cleaned_results.append(result)

    # 3. 결과 병합 + 중복 제거 + 정규화
    merger = PathMerger()
    merged = merger.merge([cleaned_results[0]]) # Pass list of lists of dicts
    merged = merger.merge([cleaned_results[0]]) # Pass list of lists of dicts
    print(f"[CrawlerTask] Merged {sum(len(r) for r in cleaned_results)} → {len(merged)} unique URLs")

    # 3.5. 메타데이터 보강 (Status Code 없는 항목 Probe)
    missing_metadata = [item for item in merged if not item.get("status_code")]
    if missing_metadata:
        urls_to_probe = [item["url"] for item in missing_metadata]
        print(f"[CrawlerTask] Probing {len(urls_to_probe)} URLs for missing metadata...")
        
        probed_data = await probe_urls(urls_to_probe)
        
        updated_count = 0
        for item in merged:
            p_data = probed_data.get(item["url"])
            if p_data and p_data.get("status_code"):
                item["status_code"] = p_data["status_code"]
                item["content_type"] = p_data.get("content_type")
                item["content_length"] = p_data.get("content_length")
                updated_count += 1
        print(f"[CrawlerTask] Updated metadata for {updated_count} URLs")

    # 4. DB 저장
    async with AsyncSessionLocalTask() as db:
        # 6. 결과 저장
        if merged: # Renamed 'all_paths' to 'merged' to match the variable name
            # 중복 제거 (이미 PathMerger에서 처리됨)
            unique_paths = merged
            await path_service.save_paths(db, subdomain_id, unique_paths)
            print(f"[CrawlerTask] Saved {len(unique_paths)} paths for {url}")
        else:
            print(f"[CrawlerTask] No paths found for {url}")
            
        # Update Subdomain Task Status (Completed)
        await db.execute(
            update(Subdomain)
            .where(Subdomain.id == subdomain_id)
            .values(task_status="Path Crawled")
        )
        await db.commit()
        
        await task_manager.decrement_task_count(subdomain.scan_id)

    await engine.dispose()

