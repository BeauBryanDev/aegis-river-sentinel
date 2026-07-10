from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AnalysisBase(BaseModel):
    video_id:      int
    frame_start:   int   = Field(..., ge=0)
    frame_end:     int   = Field(..., ge=0)
    water_ratio:   float = Field(..., ge=0.0, le=1.0)
    vel_mean:      float = Field(..., ge=0.0)
    vel_std:       float = Field(..., ge=0.0)
    vel_max:       float = Field(..., ge=0.0)
    anomaly_score: float = Field(default=0.0, ge=0.0)
    anomaly_flag:  bool  = False


class AnalysisCreate(AnalysisBase):
    pass


class AnalysisRead(AnalysisBase):
    model_config = ConfigDict(from_attributes=True)

    id:          int
    created_at:  datetime


class AnalysisSummary(BaseModel):
    """
    Lightweight version for time-series charts.
    Frontend uses this to plot vel_mean and water_ratio
    over the video timeline.
    """
    model_config = ConfigDict(from_attributes=True)

    id:            int
    frame_start:   int
    frame_end:     int
    water_ratio:   float
    vel_mean:      float
    anomaly_score: float
    anomaly_flag:  bool


class AnalysisFilter(BaseModel):
    """
    Query params for GET /analyses.
    """
    video_id:          Optional[int]  = None
    anomaly_flag:      Optional[bool] = None
    min_anomaly_score: Optional[float] = Field(default=None, ge=0.0)
    limit:             int  = Field(default=100, ge=1, le=500)
    offset:            int  = Field(default=0,   ge=0)


class TimeSeriesPoint(BaseModel):
    """
    Single data point for dashboard chart rendering.
    Optimized for Recharts consumption.
    """
    frame:         int
    water_ratio:   float
    vel_mean:      float
    anomaly_score: float


class TimeSeriesResponse(BaseModel):
    """
    Response for GET /videos/{id}/timeseries.
    Returns aggregated analysis data as a plottable series.
    """
    video_id:     int
    total_points: int
    points:       list[TimeSeriesPoint]