from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

class Technology(Base):
    __tablename__ = "technologies"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    subdomain_id = Column(String, ForeignKey("subdomains.id"), nullable=False, index=True)
    
    name = Column(String, nullable=False)
    version = Column(String, nullable=True)
    categories = Column(JSON, nullable=True) # List of category names
    
    # Relationships
    subdomain = relationship("Subdomain", back_populates="technologies")
