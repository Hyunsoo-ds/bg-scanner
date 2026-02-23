from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Subdomain(Base):
    __tablename__ = "subdomains"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"))
    hostname = Column(String, index=True)
    ip_address = Column(String, nullable=True)
    is_alive = Column(Boolean, default=False)
    status_code = Column(Integer, nullable=True)
    title = Column(String, nullable=True)
    discovered_by = Column(String, nullable=True)
    task_status = Column(String, default="pending", nullable=True)
    
    # Relationships
    scan = relationship("Scan", back_populates="subdomains")
    ports = relationship("Port", back_populates="subdomain", cascade="all, delete-orphan")
    technologies = relationship("Technology", back_populates="subdomain", cascade="all, delete-orphan")
    paths = relationship("Path", back_populates="subdomain", cascade="all, delete-orphan")
