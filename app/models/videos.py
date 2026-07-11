from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import List, Optional
from  alerts import Alert
from analysis import Analysis

from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id:          Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    location_id: Mapped[int]   = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )

    filename:    Mapped[str]   = mapped_column(String(255), nullable=False)
    filepath:    Mapped[str]   = mapped_column(String(512), nullable=False)

    fps:         Mapped[Optional[float]] = mapped_column(Float,   nullable=True)
    duration_s:  Mapped[Optional[float]] = mapped_column(Float,   nullable=True)
    width:       Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    height:      Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    total_frames:Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    status:      Mapped[str]   = mapped_column(
        String(50), nullable=False, default="pending"
    )
    error_msg:   Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at   = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at = mapped_column(DateTime(timezone=True), nullable=True)


    location  = relationship("Location")
    analyses: Mapped[List["Analysis"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    alerts:   Mapped[List["Alert"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
    

    def __repr__(self) -> str:
        return f"<Video id={self.id} filename={self.filename!r} status={self.status!r}>"