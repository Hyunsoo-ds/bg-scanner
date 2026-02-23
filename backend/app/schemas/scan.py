from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class ScanBase(BaseModel):
    target_id: str
    config: Dict[str, Any] = Field(default_factory=dict)

class ScanCreate(ScanBase):
    pass

class ScanResponse(ScanBase):
    id: str
    status: str
    phase: Optional[str] = None
    progress_percent: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
