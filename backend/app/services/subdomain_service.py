from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subdomain import Subdomain
from typing import List, Dict, Any
from sqlalchemy import select

async def save_subdomains(db: AsyncSession, scan_id: str, results: List[Dict[str, Any]]):
    # TODO: 중복 체크 로직 필요 (같은 스캔 내에서)
    # 여기서는 단순 bulk insert
    
    subdomains = []
    for res in results:
        subdomain = Subdomain(
            scan_id=scan_id,
            hostname=res.get("hostname"),
            ip_address=res.get("ip_address"),
            discovered_by=res.get("source"),
            is_alive=True # Subfinder 결과는 일단 alive라고 가정
        )
        subdomains.append(subdomain)
    
    if subdomains:
        db.add_all(subdomains)
        await db.commit()
    
    return len(subdomains)

from sqlalchemy.orm import selectinload

from sqlalchemy import func
from app.schemas.pagination import PaginatedResponse
from app.schemas.subdomain import SubdomainResponse
import math

async def get_subdomains(db: AsyncSession, scan_id: str, page: int = 1, size: int = 50) -> PaginatedResponse[SubdomainResponse]:
    # 1. Total Count
    count_query = select(func.count()).select_from(Subdomain).where(Subdomain.scan_id == scan_id)
    total = (await db.execute(count_query)).scalar_one()

    # 2. Paginated Items
    offset = (page - 1) * size
    query = (
        select(Subdomain)
        .where(Subdomain.scan_id == scan_id)
        .options(
            selectinload(Subdomain.ports),
            selectinload(Subdomain.technologies),
            selectinload(Subdomain.paths) # paths might be too heavy? but requested
        )
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(query)
    items = result.scalars().unique().all()

    # Deduplicate technologies manually
    for sub in items:
        if sub.technologies:
            unique_techs = []
            seen = set()
            for tech in sub.technologies:
                key = (tech.name, tech.version)
                if key not in seen:
                    seen.add(key)
                    unique_techs.append(tech)
            sub.technologies = unique_techs

    # 3. Calculate Pages
    pages = math.ceil(total / size) if size > 0 else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )
