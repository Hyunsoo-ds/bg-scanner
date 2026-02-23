from pydantic import BaseModel
from typing import Optional, List

class TechnologyBase(BaseModel):
    name: str
    version: Optional[str] = None
    categories: Optional[List[str]] = []

class TechnologyCreate(TechnologyBase):
    subdomain_id: str

class TechnologyResponse(TechnologyBase):
    id: str
    subdomain_id: str

    class Config:
        from_attributes = True
