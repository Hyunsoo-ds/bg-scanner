from pydantic import BaseModel
from typing import Optional


class PathBase(BaseModel):
    url: str
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    discovered_by: Optional[str] = None


class PathCreate(PathBase):
    subdomain_id: str


class PathResponse(PathBase):
    id: str
    subdomain_id: str

    class Config:
        from_attributes = True

from typing import Dict, List
from app.schemas.pagination import PaginatedResponse

class PathStats(BaseModel):
    total_paths: int
    live_count: int
    tool_counts: Dict[str, int]

class PathListResponse(PaginatedResponse[PathResponse]):
    stats: PathStats
