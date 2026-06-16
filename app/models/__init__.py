# app/models/__init__.py
from app.models.rivers import River
from app.models.locations import Location
from app.models.videos import Video
from app.models.alerts import Alert
from app.models.analysis import Analysis

__all__ = [
    "River",
    "Location",
    "Video",
    "Analysis",
    "Alert",
]