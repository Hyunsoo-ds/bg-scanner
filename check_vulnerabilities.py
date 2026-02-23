import sys
import os
import asyncio
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.vulnerability import Vulnerability

SCAN_ID = "9e39158a-88fd-4a1f-b8f9-552b4300fe2e"

async def check_db():
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        print(f"Checking DB for vulnerabilities in Scan {SCAN_ID}...")
        result = await db.execute(select(Vulnerability).where(Vulnerability.scan_id == SCAN_ID))
        vulns = result.scalars().all()
        print(f"Found {len(vulns)} vulnerabilities.")
        for v in vulns:
            print(f"- {v.name} ({v.severity})")

if __name__ == "__main__":
    asyncio.run(check_db())
