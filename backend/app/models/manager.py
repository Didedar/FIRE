import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.database import Base


class Manager(Base):
    __tablename__ = "managers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    position = Column(String(100), nullable=False)  # Спец, Ведущий спец, Глав спец
    skills = Column(ARRAY(String), default=[])  # VIP, ENG, KZ
    business_unit_id = Column(UUID(as_uuid=True), ForeignKey("business_units.id"), nullable=True)
    current_load = Column(Integer, default=0)

    business_unit = relationship("BusinessUnit", back_populates="managers")
    distributions = relationship("Distribution", back_populates="manager")
