from pydantic import BaseModel
from typing import Optional

class PortBase(BaseModel):
    port_number: int
    protocol: str = "tcp"
    service_name: Optional[str] = None
    state: str = "open"
    version: Optional[str] = None

class PortCreate(PortBase):
    subdomain_id: str

class PortResponse(PortBase):
    id: str
    subdomain_id: str

    class Config:
        from_attributes = True
