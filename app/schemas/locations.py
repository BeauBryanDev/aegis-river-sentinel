from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    river_id:      int
    river_segment: str   = Field(..., max_length=150)
    region:        str   = Field(..., max_length=100)
    latitude:      float = Field(..., ge=-90.0,  le=90.0)
    longitude:     float = Field(..., ge=-180.0, le=180.0)
    avg_width_m:   Optional[float] = Field(default=None, gt=0.0)


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    """
    Partial update. All fields optional.
    """
    river_segment: Optional[str]   = Field(default=None, max_length=150)
    region:        Optional[str]   = Field(default=None, max_length=100)
    latitude:      Optional[float] = Field(default=None, ge=-90.0,  le=90.0)
    longitude:     Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    avg_width_m:   Optional[float] = Field(default=None, gt=0.0)


class LocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id:          int
    created_at:  datetime


class LocationSummary(BaseModel):
    """
    Lightweight version for embedding in other responses,
    e.g. inside a River detail or a Video record.
    """
    model_config = ConfigDict(from_attributes=True)

    id:            int
    river_segment: str
    region:        str
    latitude:      float
    longitude:     float