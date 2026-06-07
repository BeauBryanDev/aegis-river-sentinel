from pydantic_settings import BaseSettings
from typing import list


class Settings(BaseSettings):
    ENVIRONMENT:           str  = "development"
    DATABASE_URL:          str
    MODEL_SEGFORMER_PATH:  str  = "weights/segformer_best.onnx"
    MODEL_RAFT_PATH:       str  = "weights/raft_small.pth"
    ALLOWED_ORIGINS:       list[str] = ["http://localhost:3000"]
    MAX_VIDEO_SIZE_MB:     int  = 50
    UPLOAD_DIR:            str  = "/tmp/riverwatch_uploads"

    class Config:
        env_file = ".env"


settings = Settings()