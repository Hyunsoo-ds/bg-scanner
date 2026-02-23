from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.path import Path
from app.models.subdomain import Subdomain
from typing import List, Dict, Any


async def save_paths(db: AsyncSession, subdomain_id: str, results: List[Dict[str, Any]]) -> int:
    """
    크롤링 결과를 paths 테이블에 저장합니다.
    같은 subdomain_id + url 조합이 이미 존재하면 스킵합니다.
    """
    if not results:
        return 0

    # 기존 Path 객체 조회 (UPSERT를 위해)
    existing_query = select(Path).where(Path.subdomain_id == subdomain_id)
    existing_result = await db.execute(existing_query)
    existing_paths = {p.url: p for p in existing_result.scalars().all()}

    new_paths = []
    
    for res in results:
        url = res.get("url", "").strip()
        if not url:
            continue
            
        status_code = res.get("status_code")
        content_type = res.get("content_type")
        content_length = res.get("content_length")
        discovered_by = res.get("discovered_by")

        if url in existing_paths:
            # Update existing path
            path = existing_paths[url]
            # Update fields if new data is available
            if status_code is not None:
                path.status_code = status_code
            if content_type:
                path.content_type = content_type
            if content_length:
                path.content_length = content_length
            # discovered_by logic: maybe append or keep? simpler to keep first or update.
            # let's not overwrite discovered_by if it exists, or maybe update if None
            if not path.discovered_by and discovered_by:
                path.discovered_by = discovered_by
        else:
            # Create new path
            path = Path(
                subdomain_id=subdomain_id,
                url=url,
                status_code=status_code,
                content_type=content_type,
                content_length=content_length,
                discovered_by=discovered_by,
            )
            new_paths.append(path)
            existing_paths[url] = path # prevent duplicates in same batch

    if new_paths:
        db.add_all(new_paths)
    
    # Commit updates and inserts
    await db.commit()

    total_ops = len(results)
    print(f"[path_service] Processed {total_ops} paths (Inserts: {len(new_paths)}) for subdomain {subdomain_id}")
    return total_ops


async def get_paths(db: AsyncSession, subdomain_id: str) -> List[Path]:
    """서브도메인별 경로 목록 조회"""
    query = select(Path).where(Path.subdomain_id == subdomain_id)
    result = await db.execute(query)
    return result.scalars().all()


# Imports for path pagination
from sqlalchemy import func
import math
from app.schemas.pagination import PaginatedResponse
from app.schemas.path import PathResponse, PathListResponse, PathStats


async def get_paths_by_scan(
    db: AsyncSession, 
    scan_id: str, 
    page: int = 1, 
    size: int = 50,
    search: str = None,
    status_category: str = None, # 2xx, 3xx, 4xx, 5xx, none
    tool: str = None,
    port: str = None
) -> PathListResponse: # Return PathListResponse instead of plain PaginatedResponse
    """스캔 ID 기준으로 경로 조회 (필터링 + 통계 포함)"""
    offset = (page - 1) * size

    # 1. Base Query (Scan Join)
    base_query = (
        select(Path)
        .join(Subdomain, Path.subdomain_id == Subdomain.id)
        .where(Subdomain.scan_id == scan_id)
    )

    # 2. Global Statistics (Unfiltered)
    # Total Paths
    total_query = (
        select(func.count(Path.id))
        .join(Subdomain, Path.subdomain_id == Subdomain.id)
        .where(Subdomain.scan_id == scan_id)
    )
    total_paths = (await db.execute(total_query)).scalar_one()

    # Live Paths (2xx/3xx)
    live_query = total_query.where(Path.status_code >= 200, Path.status_code < 400)
    live_count = (await db.execute(live_query)).scalar_one()

    # Tool Distribution
    tool_query = (
        select(Path.discovered_by, func.count(Path.id))
        .join(Subdomain, Path.subdomain_id == Subdomain.id)
        .where(Subdomain.scan_id == scan_id)
        .group_by(Path.discovered_by)
    )
    tool_counts_res = (await db.execute(tool_query)).all()
    tool_counts = {row[0] or "unknown": row[1] for row in tool_counts_res}

    # 3. Filtering Logic
    filter_conditions = []
    if search:
        filter_conditions.append(Path.url.ilike(f"%{search}%"))
    
    if status_category:
        if status_category == "2xx":
            filter_conditions.append(Path.status_code.between(200, 299))
        elif status_category == "3xx":
            filter_conditions.append(Path.status_code.between(300, 399))
        elif status_category == "4xx":
            filter_conditions.append(Path.status_code.between(400, 499))
        elif status_category == "5xx":
            filter_conditions.append(Path.status_code >= 500)
        elif status_category == "none":
            filter_conditions.append(Path.status_code == None)
        # 'all' implies no condition

    if tool and tool != "all":
        filter_conditions.append(Path.discovered_by == tool)

    # Port filtering logic (URLs are stored as full strings)
    if port and port != "all":
        from sqlalchemy import or_
        if port == "80":
            filter_conditions.append(or_(
                Path.url.like("%:80/%"),
                Path.url.like("%:80"),
                Path.url.like("http://%"), # implicit 80
            ))
        elif port == "443":
            filter_conditions.append(or_(
                Path.url.like("%:443/%"),
                Path.url.like("%:443"),
                Path.url.like("https://%"), # implicit 443
            ))
        else:
            filter_conditions.append(or_(
                Path.url.like(f"%:{port}/%"),
                Path.url.like(f"%:{port}")
            ))

    # Apply filters
    filtered_query = base_query
    if filter_conditions:
        filtered_query = filtered_query.where(*filter_conditions)

    # 4. Filtered Count
    count_subquery = (
        select(func.count())
        .select_from(filtered_query.subquery())
    )
    filtered_total = (await db.execute(count_subquery)).scalar_one()

    # 5. Paginated Items
    items_query = filtered_query.offset(offset).limit(size)
    result = await db.execute(items_query)
    items = result.scalars().all()

    # 6. Calculate Pages
    pages = math.ceil(filtered_total / size) if size > 0 else 0

    return PathListResponse(
        items=items,
        total=filtered_total,
        page=page,
        size=size,
        pages=pages,
        stats=PathStats(
            total_paths=total_paths,
            live_count=live_count,
            tool_counts=tool_counts
        )
    )
