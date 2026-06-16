from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id:          Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    video_id:    Mapped[int]   = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[int]   = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )

    frame_num:   Mapped[int]   = mapped_column(Integer, nullable=False)

    alert_type:  Mapped[str]   = mapped_column(String(100), nullable=False)
    severity:    Mapped[str]   = mapped_column(String(50),  nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    acknowledged:     Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at   = mapped_column(DateTime(timezone=True), nullable=True)

    created_at        = mapped_column(DateTime(timezone=True), server_default=func.now())

    video    = relationship("Video",    back_populates="alerts")
    analysis = relationship("Analysis", back_populates="alerts")

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} "
            f"type={self.alert_type!r} "
            f"severity={self.severity!r}>"
        )
        
        