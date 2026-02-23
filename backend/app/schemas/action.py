from pydantic import BaseModel
from typing import List, Literal

class ActionRequest(BaseModel):
    subdomain_ids: List[str] = []
    path_ids: List[str] = []
    action: Literal["port_scan", "tech_profiling", "path_crawling", "nuclei_scan"]
    
class ActionResponse(BaseModel):
    message: str
    triggered_count: int
