from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AlertSeverity(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


class AlertType(str, Enum):
    WATER_LEVEL_RISE = "water_level_rise"
    VELOCITY_SPIKE   = "velocity_spike"
    FLOW_DISTURBANCE = "flow_disturbance"
    TURBULENCE       = "turbulence"
    GENERIC_ANOMALY  = "generic_anomaly"


class AlertBase(BaseModel):
    video_id:    int
    analysis_id: int
    frame_num:   int  = Field(..., ge=0)
    alert_type:  AlertType
    severity:    AlertSeverity
    description: Optional[str] = None


class AlertCreate(AlertBase):
    pass


class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    acknowledged:     bool
    acknowledged_at:  Optional[datetime]
    created_at:       datetime


class AlertSummary(BaseModel):
    """
    Lightweight version for lists and dashboards.
    """
    model_config = ConfigDict(from_attributes=True)

    id:    int
    video_id:     int
    frame_num:    int
    alert_type:   str
    severity:     str
    acknowledged: bool
    created_at:   datetime


class AlertAcknowledge(BaseModel):
    """
    Payload for the acknowledge endpoint.
    Empty on purpose. Ack timestamp is set server-side.
    """
    pass


class AlertFilter(BaseModel):
    """
    Query params for GET /alerts with filtering.
    Used via Depends() in the router.
    """
    video_id:     Optional[int]           = None
    severity:     Optional[AlertSeverity] = None
    alert_type:   Optional[AlertType]     = None
    acknowledged: Optional[bool]          = None
    limit:        int  = Field(default=50, ge=1, le=200)
    offset:       int  = Field(default=0,  ge=0)