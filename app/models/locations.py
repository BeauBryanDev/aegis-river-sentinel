from sqlalchemy import String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


from app.core.database import Base


class Location(Base):
    __tablename__ = "locations"

    id:          Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    river_id:    Mapped[int]   = mapped_column(ForeignKey("rivers.id", ondelete="CASCADE"), nullable=False)

    river_segment: Mapped[str]   = mapped_column(String(150), nullable=False)
    region:        Mapped[str]   = mapped_column(String(100), nullable=False)

    latitude:      Mapped[float] = mapped_column(Float, nullable=False)
    longitude:     Mapped[float] = mapped_column(Float, nullable=False)
    avg_width_m:   Mapped[float] = mapped_column(Float, nullable=True)

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    river = relationship("River", back_populates="locations")


    def __repr__(self) -> str:
        return f"<Location id={self.id} river_segment={self.river_segment!r} region={self.region!r}>"
    
    