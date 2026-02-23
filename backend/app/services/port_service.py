from sqlalchemy.ext.asyncio import AsyncSession
from app.models.port import Port
from typing import List, Dict, Any
from sqlalchemy import select

async def save_ports(db: AsyncSession, subdomain_id: str, results: List[Dict[str, Any]]):
    ports = []
    print(f"Saving {len(results)} ports for subdomain {subdomain_id}")
    for res in results:
        port = Port(
            subdomain_id=subdomain_id,
            port_number=res.get("port_number"),
            protocol=res.get("protocol"),
            service_name=res.get("service_name"),
            state=res.get("state"),
            version=res.get("version")
        )
        ports.append(port)
    
    if ports:
        db.add_all(ports)
        await db.commit()
    
    return len(ports)

async def get_ports(db: AsyncSession, subdomain_id: str) -> List[Port]:
    query = select(Port).where(Port.subdomain_id == subdomain_id)
    result = await db.execute(query)
    return result.scalars().all()
