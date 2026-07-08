# RiverWatch

River anomaly detection and surface velocity estimation [px/s] from fixed-camera video footage.

<img src="./frontend/src/assets/river_watch_icon.webp" alt="Optical water flow" width="250" style="display:block; margin:8px auto; border-radius:8px;" />

## Overview

RiverWatch is a computer vision system designed to monitor river behavior from fixed-camera video footage. The system segments the water surface using a fine-tuned SegFormer model, estimates surface flow velocity using RAFT optical flow, and detects anomalous behavior through statistical analysis of the velocity field over time.

The primary use case is early detection of hydrological anomalies such as flash floods, sudden velocity changes, and abnormal water level rise in Andean river systems.

## Architecture

```
Video Input (.mp4)
        |
        v
Frame Diff Filter          -- discard static frames before GPU
        |
        v
SegFormer-B2               -- semantic segmentation, water mask extraction
(fine-tuned, 7 classes)    -- runs every 100 frames + histogram trigger
        |
        v
Water ROI Mask             -- binary mask, water pixels only
        |
        v
RAFT-Small                 -- optical flow on water ROI exclusively
(torchvision)              -- background discarded, GPU load reduced
        |
        v
Velocity Field (px/frame)  -- magnitude + direction per pixel
        |
   +----+----+
   |         |
   v         v
Heatmap    Z-Score         -- COLORMAP_JET visualization
           Anomaly         -- sliding window, multivariable
           Detector        -- vel_mean, vel_std, water_ratio
        |
        v
PostgreSQL                 -- persist only when anomaly_score > threshold
        |
        v
FastAPI + WebSocket        -- async processing via Celery + Redis
        |
        v
React Dashboard            -- velocity time series + heatmap overlay
```

## Models

**SegFormer-B2** fine-tuned on two datasets with partial label training:

- RIWA (River Water Segmentation Dataset): 1,632 images, binary water/background labels
- Parepare Flood Dataset: 3,748 images, 7-class semantic annotations

Class schema:

| Index | Class      | Source          |
|-------|------------|-----------------|
| 0     | background | RIWA            |
| 1     | water      | RIWA + Parepare |
| 2     | sky        | Parepare        |
| 3     | vegetation | Parepare        |
| 4     | building   | Parepare        |
| 5     | vehicle    | Parepare        |
| 6     | person     | Parepare        |

Training strategy: three-stage curriculum learning starting from `nvidia/mit-b2` ImageNet checkpoint, multi-dataset fine-tuning with `ignore_index=255` for partial supervision, and domain fine-tuning on Andean river footage.

**RAFT-Small** (torchvision, `Raft_Small_Weights.C_T_V2`) for dense optical flow estimation. Applied exclusively on the water ROI provided by SegFormer.

## Anomaly Detection

Anomaly scoring uses a sliding window Z-score over three metrics computed per frame:

- `vel_mean`: mean flow magnitude in px/frame over water pixels
- `vel_std`: standard deviation of flow magnitude
- `water_ratio`: fraction of frame classified as water

A frame is flagged as anomalous when any metric deviates more than `ANOMALY_Z_THRESHOLD` standard deviations from the sliding window mean. Default window size is 150 frames (5 seconds at 30 fps).

## Pipeline Optimizations

**Heartbeat filter**: frame absolute difference computed before GPU inference. Frames with mean pixel difference below `FRAME_DIFF_THRESHOLD` are discarded immediately.

**SegFormer interval**: segmentation runs every `SEGFORMER_INTERVAL` frames (default: 100, approximately every 4 seconds at 30 fps). Re-triggered if water histogram changes significantly between intervals.

**ROI masking**: RAFT receives only water-masked frames. Background pixels are set to zero before inference, reducing effective computation and eliminating flow noise from static scene elements.

**Async inference**: video processing is enqueued via Celery and processed by a GPU worker independently of the HTTP request lifecycle.

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | FastAPI, Python 3.11                    |
| ML Runtime | PyTorch 2.4, ONNX Runtime, torchvision  |
| CV         | OpenCV, Pillow                          |
| Queue      | Celery + Redis                          |
| Database   | PostgreSQL 16                           |
| Frontend   | React, TypeScript, Tailwind, Recharts   |
| Deploy     | Docker, AWS EC2 g4dn.xlarge (T4 GPU)    |

## Project Structure

```
river-watch/
    app/
        core/           config, database, logging
        models/         SQLAlchemy ORM models
        routers/        FastAPI route handlers
        schemas/        Pydantic request/response schemas
        services/       pipeline, segformer, raft, detection
        utils/          video utilities, flow heatmap, stream processing
    weights/
        best_model.pt           SegFormer-B2 fine-tuned checkpoint
        raft_small.pth          RAFT-Small torchvision weights
    sql/
        init.sql                database schema, no migration framework
    tests/
    ml/                         training notebooks (Colab)
    docker-compose.yml
    Dockerfile
    requirements.txt            production, CUDA 12.1
    requirements-dev.txt        development, CPU only
```

## Setup

**Prerequisites**: Docker, Docker Compose, NVIDIA Container Toolkit (production only).

```bash
git clone https://github.com/your-username/river-watch.git
cd river-watch

cp .env.example .env
# edit .env with your credentials

docker-compose up db -d
docker-compose up backend -d
```

Backend available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

Place model weights in `weights/` before starting the backend:

```
weights/best_model.pt
weights/raft_small.pth
```

## Environment Variables

| Variable               | Description                              | Default                  |
|------------------------|------------------------------------------|--------------------------|
| `DATABASE_URL`         | PostgreSQL connection string             | required                 |
| `MODEL_SEGFORMER_PATH` | Path to SegFormer checkpoint             | `weights/best_model.pt`  |
| `MODEL_RAFT_PATH`      | Path to RAFT-Small weights               | `weights/raft_small.pth` |
| `SEGFORMER_INTERVAL`   | Frames between segmentation runs         | `100`                    |
| `FRAME_DIFF_THRESHOLD` | Minimum frame difference to process      | `15.0`                   |
| `ANOMALY_Z_THRESHOLD`  | Standard deviations for anomaly flag     | `2.0`                    |
| `SLIDING_WINDOW_SIZE`  | Frames in anomaly detection window       | `150`                    |
| `UPLOAD_DIR`           | Temporary video storage path             | `/tmp/riverwatch_uploads`|
| `MAX_VIDEO_MB`         | Maximum upload size in MB                | `500`                    |

## Limitations

Optical flow velocity is expressed in px/frame, not physical units. Conversion to m/s requires camera calibration and homography estimation, which is outside the current scope. Velocity magnitude is perspective-dependent: objects at greater distances from the camera produce smaller pixel displacements at equivalent physical velocities. This effect is documented and should be considered when interpreting results from wide-angle river footage.

The SegFormer model was trained primarily on flood imagery from South Sulawesi, Indonesia (Parepare dataset) and a global river/water dataset (RIWA). Performance on Andean river conditions (high sediment load, variable illumination, riparian vegetation) was validated on a limited set of footage from the Chicamocha, Sogamoso, and Fonce rivers in Santander, Colombia.

## Academic Context

This project was developed as part of the Artificial Intelligence II course at a university in Bogota, Colombia. The system targets commu

nity-level flood early warning in Andean river basins.

## License

MIT