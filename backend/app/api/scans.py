from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.scan import ScanCreate, ScanResponse
from app.services import scan_service, subdomain_service, path_service, vulnerability_service
from app.schemas.subdomain import SubdomainResponse
from app.schemas.subdomain import SubdomainResponse
from app.schemas.path import PathResponse, PathListResponse

router = APIRouter()

from app.services.task_manager import task_manager

@router.post("", response_model=ScanResponse)
async def create_scan(scan: ScanCreate, db: AsyncSession = Depends(get_db)):
    new_scan = await scan_service.create_scan(db, scan)
    await task_manager.increment_task_count(new_scan.id, 1)
    return new_scan

@router.get("", response_model=List[ScanResponse])
async def read_scans(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await scan_service.get_scans(db, skip, limit)

@router.get("/{scan_id}", response_model=ScanResponse)
async def read_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    scan = await scan_service.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

from app.schemas.pagination import PaginatedResponse
from fastapi import Query

@router.get("/{scan_id}/subdomains", response_model=PaginatedResponse[SubdomainResponse])
async def read_scan_subdomains(
    scan_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    return await subdomain_service.get_subdomains(db, scan_id, page, size)


@router.get("/{scan_id}/paths", response_model=PathListResponse)
async def read_scan_paths(
    scan_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: str = Query(None),
    status_category: str = Query(None),
    tool: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """스캔에서 발견된 모든 경로(URL) 목록 조회"""
    return await path_service.get_paths_by_scan(
        db, 
        scan_id, 
        page, 
        size,
        search=search,
        status_category=status_category,
        tool=tool
    )

from app.schemas.vulnerability import VulnerabilityResponse

@router.get("/{scan_id}/vulnerabilities", response_model=PaginatedResponse[VulnerabilityResponse])
async def read_scan_vulnerabilities(
    scan_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    severity: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """스캔에서 발견된 취약점 목록 조회"""
    return await vulnerability_service.get_vulnerabilities(db, scan_id, page, size, severity)

from app.schemas.action import ActionRequest, ActionResponse
from app.workers.port_task import run_port_scan
from app.workers.tech_task import run_tech_scan
from app.workers.crawler_task import run_path_crawl
from app.workers.nuclei_task import run_nuclei_scan
from app.workers.celery_app import celery_app
from app.models.subdomain import Subdomain
from app.models.path import Path
from app.models.port import Port
from sqlalchemy import select

@router.post("/{scan_id}/actions", response_model=ActionResponse)
async def trigger_scan_action(
    scan_id: str,
    action_req: ActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    특정 서브도메인이나 경로들에 대해 Port Scan, Tech Profiling, Path Crawling, Nuclei Scan 수동 실행
    """
    subdomain_ids = action_req.subdomain_ids
    path_ids = action_req.path_ids
    action = action_req.action
    
    triggered_count = 0
    
    # Verify subdomains belong to scan
    # (Optional optimization: fetch all at once)
    
    if action == "port_scan":
        for sub_id in subdomain_ids:
            # Task Count 증가
            await task_manager.increment_task_count(scan_id, 1)
            run_port_scan.delay(sub_id)
            triggered_count += 1
            
    elif action == "tech_profiling" or action == "path_crawling":
        # Tech/Path Crawl을 위해서는 URL이 필요함.
        # DB에서 Subdomain 정보와 Port 정보를 조회해서 URL을 구성해야 함.
        # 간단하게: 80/443이 열려있거나, http/https 서비스가 있는 포트를 찾음.
        
        # 1. 서브도메인 조회 check
        query = select(Subdomain).where(Subdomain.id.in_(subdomain_ids))
        result = await db.execute(query)
        subdomains = result.scalars().all()
        
        for sub in subdomains:
            if sub.scan_id != scan_id:
                continue # Wrong scan
                
            # 포트 조회
            p_query = select(Port).where(Port.subdomain_id == sub.id)
            p_res = await db.execute(p_query)
            ports = p_res.scalars().all()
            
            urls = []
            target_host = sub.ip_address if sub.ip_address else sub.hostname
            
            # URL 구성 로직 (port_task와 유사)
            # 만약 포트 스캔을 안 해서 포트가 없다면? -> 기본적으로 http://, https:// 시도해볼 수 있음.
            # 하지만 포트 스캔 없이는 정확도가 떨어짐. 사용자가 포트스캔을 먼저 하도록 유도하거나, 강제로 80/443 가정.
            
            if not ports:
                # 포트 정보가 없으면 기본 80/443 추가
                urls.append(f"http://{target_host}")
                urls.append(f"https://{target_host}")
            else:
                for port in ports:
                    svc = port.service_name
                    num = port.port_number
                    if svc in ["http", "https", "http-alt"] or num in [80, 443, 8080, 8443]:
                        if num == 80: urls.append(f"http://{target_host}")
                        elif num == 443: urls.append(f"https://{target_host}")
                        elif num == 8443: urls.append(f"https://{target_host}:{num}")
                        elif svc == "https": urls.append(f"https://{target_host}:{num}")
                        else: urls.append(f"http://{target_host}:{num}")
            
            # 중복 제거
            urls = list(set(urls))
            
            for url in urls:
                if action == "tech_profiling":
                    await task_manager.increment_task_count(scan_id, 1)
                    run_tech_scan.delay(sub.id, url)
                    triggered_count += 1
                elif action == "path_crawling":
                    await task_manager.increment_task_count(scan_id, 1)
                    celery_app.send_task("app.workers.crawler_task.run_path_crawl", args=[sub.id, url])
                    triggered_count += 1

    elif action == "nuclei_scan":
        if path_ids:
            # Path 대상 스캔
            query = select(Path).where(Path.id.in_(path_ids))
            result = await db.execute(query)
            paths = result.scalars().all()
            
            for path in paths:
                # 스캔 유효성 체크는 생략하거나 강화 가능
                
                await task_manager.increment_task_count(scan_id, 1)
                run_nuclei_scan.delay(scan_id, path.url, path_id=path.id, subdomain_id=path.subdomain_id)
                triggered_count += 1

    return ActionResponse(message=f"Triggered {action} for {triggered_count} targets", triggered_count=triggered_count)
