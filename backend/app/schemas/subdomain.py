from pydantic import BaseModel
from typing import Optional

class SubdomainBase(BaseModel):
    hostname: str
    ip_address: Optional[str] = None
    is_alive: bool = False
    
class SubdomainCreate(SubdomainBase):
    scan_id: str
    discovered_by: Optional[str] = None

from typing import List, Optional
from .port import PortResponse
from .technology import TechnologyResponse
from .path import PathResponse

class SubdomainResponse(SubdomainBase):
    id: str
    scan_id: str
    discovered_by: Optional[str] = None
    ports: List[PortResponse] = []
    technologies: List[TechnologyResponse] = []
    paths: List[PathResponse] = []
    task_status: Optional[str] = "pending"
    
    class Config:
        from_attributes = True

