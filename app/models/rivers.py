from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import List

from app.core.database import Base


class River(Base):
    __tablename__ = "rivers"

    id:          Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    name:        Mapped[str]   = mapped_column(String(100), nullable=False)
    country:     Mapped[str]   = mapped_column(String(100), nullable=False)
    length_km:   Mapped[float] = mapped_column(Float, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    locations: Mapped[List["Location"]] = relationship(
        back_populates="river",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<River id={self.id} name={self.name!r} country={self.country!r}>"
    
    