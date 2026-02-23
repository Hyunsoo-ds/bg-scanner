import sys
import os
import asyncio
import uuid

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.scan import Scan
from app.models.subdomain import Subdomain
from app.models.path import Path
from app.models.vulnerability import Vulnerability

DOMAIN = "hackthissite.org"

async def seed_data():
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # 1. Find the scan we created (most recent for domain)
        # We assume the scan exists from previous script run
        result = await db.execute(select(Scan).order_by(Scan.started_at.desc()).limit(1))
        scan = result.scalar_one_or_none()
        
        if not scan:
            print("No scan found. Please run verify_nuclei_trigger.py first (partial run).")
            return

        print(f"Seeding data for Scan ID: {scan.id}")

        # 2. Create Subdomain
        sub_id = str(uuid.uuid4())
        sub = Subdomain(
            id=sub_id,
            scan_id=scan.id,
            hostname=f"www.{DOMAIN}",
            is_alive=True,
            ip_address="1.1.1.1"
        )
        db.add(sub)
        
        # 3. Create Path
        path_id = str(uuid.uuid4())
        path = Path(
            id=path_id,
            subdomain_id=sub_id,
            url=f"http://www.{DOMAIN}/robots.txt",
            status_code=200,
            discovered_by="manual_seed"
        )
        db.add(path)
        
        await db.commit()
        print(f"Seeded Subdomain {sub_id} and Path {path_id}")

if __name__ == "__main__":
    asyncio.run(seed_data())
