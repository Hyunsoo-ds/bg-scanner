import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.vulnerability import Vulnerability
from app.models.scan import Scan
from app.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get a scan id to link
        result = await db.execute(select(Scan.id).limit(1))
        scan_id = result.scalar_one_or_none()
        if not scan_id:
            print("No scan_id found")
            return
            
        print(f"Using scan_id: {scan_id}")
        
        vuln = Vulnerability(
            scan_id=scan_id,
            name="Nuclei Insert Test",
            severity="high",
            description="Test from script",
            matcher_name="test-matcher",
            extracted_results='["test"]'
        )
        db.add(vuln)
        await db.commit()
        print("Commit completed!")

asyncio.run(main())
