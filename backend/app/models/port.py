from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base
import uuid

class Port(Base):
    __tablename__ = "ports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subdomain_id = Column(String, ForeignKey("subdomains.id", ondelete="CASCADE"))
    
    port_number = Column(Integer, nullable=False)
    protocol = Column(String, default="tcp") # tcp, udp
    service_name = Column(String, nullable=True) # http, ssh, etc.
    state = Column(String, default="open") # open, closed, filtered
    version = Column(String, nullable=True) # nginx 1.18.0, etc.
    
    subdomain = relationship("Subdomain", back_populates="ports")
