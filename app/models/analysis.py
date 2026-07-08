from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional
from  alerts import Alert

from app.core.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id:            Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    video_id:      Mapped[int]   = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )

    frame_start:   Mapped[int]   = mapped_column(Integer, nullable=False)
    frame_end:     Mapped[int]   = mapped_column(Integer, nullable=False)

    water_ratio:   Mapped[float] = mapped_column(Float, nullable=False)
    vel_mean:      Mapped[float] = mapped_column(Float, nullable=False)
    vel_std:       Mapped[float] = mapped_column(Float, nullable=False)
    vel_max:       Mapped[float] = mapped_column(Float, nullable=False)

    anomaly_score: Mapped[float] = mapped_column(Float,   nullable=False, default=0.0)
    anomaly_flag:  Mapped[bool]  = mapped_column(Boolean, nullable=False, default=False)

    created_at     = mapped_column(DateTime(timezone=True), server_default=func.now())

    video   = relationship("Video", back_populates="analyses")
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis id={self.id} "
            f"frames={self.frame_start}-{self.frame_end} "
            f"anomaly={self.anomaly_flag}>"
        )

