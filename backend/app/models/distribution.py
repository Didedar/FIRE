import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Distribution(Base):
    __tablename__ = "distributions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False, unique=True)
    ai_analysis_id = Column(UUID(as_uuid=True), ForeignKey("ai_analyses.id"), nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("managers.id"), nullable=False)
    reason = Column(String(500), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="distribution")
    ai_analysis = relationship("AIAnalysis", back_populates="distribution")
    manager = relationship("Manager", back_populates="distributions")
