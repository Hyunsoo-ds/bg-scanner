from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class TargetBase(BaseModel):
    domain: str = Field(..., description="Target domain (e.g., example.com)")

class TargetCreate(TargetBase):
    pass

class TargetResponse(TargetBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
