import uuid
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False, unique=True)
    type = Column(String(100), nullable=False)  # Жалоба, Смена данных, etc.
    tonality = Column(String(50), nullable=False)  # Позитивный, Нейтральный, Негативный
    priority = Column(Integer, nullable=False)  # 1-10
    language = Column(String(10), nullable=False, default="RU")  # KZ, ENG, RU
    summary = Column(Text, nullable=True)
    geo_latitude = Column(Float, nullable=True)
    geo_longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="ai_analysis")
    distribution = relationship("Distribution", back_populates="ai_analysis", uselist=False)
