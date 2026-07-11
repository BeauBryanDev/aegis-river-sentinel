from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.locations import LocationSummary


class RiverBase(BaseModel):
    name:      str             = Field(..., max_length=100)
    country:   str             = Field(..., max_length=100)
    length_km: Optional[float] = Field(default=None, gt=0.0)


class RiverCreate(RiverBase):
    pass


class RiverUpdate(BaseModel):
    """
    Partial update. All fields optional.
    """
    name:      Optional[str]   = Field(default=None, max_length=100)
    country:   Optional[str]   = Field(default=None, max_length=100)
    length_km: Optional[float] = Field(default=None, gt=0.0)


class RiverRead(RiverBase):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    created_at: datetime


class RiverSummary(BaseModel):
    """
    Lightweight version for embedding in other responses,
    e.g. inside a Location detail.
    """
    model_config = ConfigDict(from_attributes=True)

    id:      int
    name:    str
    country: str


class RiverDetail(RiverRead):
    """
    Full river record with its associated locations.
    """
    locations: List[LocationSummary] = Field(default_factory=list)
