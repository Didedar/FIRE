import uuid
from sqlalchemy import Column, String, Date, Float, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_guid = Column(String(255), nullable=False)
    gender = Column(String(20), nullable=True)
    birth_date = Column(Date, nullable=True)
    segment = Column(String(50), nullable=False, default="Mass")  # Mass, VIP, Priority
    description = Column(Text, nullable=True)
    attachments = Column(String(500), nullable=True)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    street = Column(String(200), nullable=True)
    house = Column(String(50), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String(50), default="new")  # new, analyzed, distributed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ai_analysis = relationship("AIAnalysis", back_populates="ticket", uselist=False)
    distribution = relationship("Distribution", back_populates="ticket", uselist=False)
