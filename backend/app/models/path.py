from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
import uuid


class Path(Base):
    __tablename__ = "paths"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subdomain_id = Column(String, ForeignKey("subdomains.id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(String, nullable=False)
    status_code = Column(Integer, nullable=True)
    content_type = Column(String, nullable=True)
    content_length = Column(Integer, nullable=True)
    discovered_by = Column(String, nullable=True)  # katana|dirsearch|waybackurls|gau

    # Relationships
    subdomain = relationship("Subdomain", back_populates="paths")
