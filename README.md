# Pickleball AI MVP — React + FastAPI + YOLO11 + ByteTrack

A runnable proof-of-concept for **offline processing of uploaded MP4 video**. No live camera, speed measurement, ball tracking or automatic scoring.

## Quick start (Docker recommended)

Requirements: Docker Engine / Docker Desktop with Compose, internet **for first build and first YOLO model download**.

```bash
docker compose up --build
```

Open **http://localhost:8080**. Upload a short H.264 MP4. Optionally click the four *outer* court corners in this order: **top-left, top-right, bottom-right, bottom-left**, as seen in the video image (not necessarily the actual near/far order). Click **Analyze Video**. Wait for the result; processing is asynchronous. Download annotated video or JSON.

For deployment on a VPS, install Docker Compose, clone/unzip the repository, run `docker compose up -d --build`, configure DNS, and **put an HTTPS reverse proxy with authentication in front of port 8080** (Caddy, Traefik or Nginx + TLS). Do not expose this prototype publicly without the production hardening below.

## Architecture

- `frontend`: Vite + React; served by Nginx, which proxies `/api` to backend.
- `backend`: FastAPI with file upload, job status polling and static result endpoints.
- `processor.py`: OpenCV video decoding, pretrained YOLO11n person detection, ByteTrack ID assignment, optional homography calibration, heatmap and export.
- Docker volume `pickleball_data` stores uploaded and generated files.

### API

- `GET /api/health`
- `POST /api/jobs`: multipart `video` MP4 and optional `corners` JSON (`[[x,y],...]`, normalized 0–1)
- `GET /api/jobs/{id}`: status, progress, errors
- `GET /api/jobs/{id}/files/{filename}`: `annotated.mp4`, `heatmap.png`, `court.png`, `positions.json`, `summary.json`

## Development without Docker

Backend (Python 3.11 recommended; FFmpeg executable recommended):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
DATA_DIR=./data uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Vite proxy is already configured in `frontend/vite.config.js`.

Then open http://localhost:5173.

## Important limitations

1. **MVP, not validated production AI**. Generic person detector may include bystanders, miss small people or switch identities. The current simple mapping assigns slots P1–P4 to the first four distinct tracker IDs and **does not recover from ID switches**. Use a fixed camera with all four players clearly visible and few bystanders.
2. Court and heatmap require clicking **four court corners**. Without calibration the system produces only annotated video. Perspective transform assumes a planar court. The four corners must correspond to the outer court boundaries, consistently ordered; reversed corners will distort results.
3. Heatmap counts detected player foot positions, not measured time in zones, and combines all four players. The court map displays the last detected positions. At `INFERENCE_STRIDE=2`, only every second frame is analyzed and intermediate frames are unannotated.
4. On CPU, a 5-minute 1080p video may take substantially longer than 5 minutes. Start with 30–60 seconds for testing. Processing time depends on CPU/GPU and model.
5. Uploaded video and results expire after 30 minutes or can be deleted explicitly (see retention details below). File size limit is 600 MB. There is no authentication, queue persistence, user isolation, upload quota, antivirus scanning, video transcoding validation, or concurrency limiting. Only use on trusted networks until these are added.
6. Jobs use in-process background threads: restarting the backend interrupts them. Use Redis + RQ/Celery for a real deployment, along with database records, durable object storage, user auth, retention policy, signed downloads, file validation and resource limits.
7. Ultralytics licensing may require an AGPL-3.0-compliant release or commercial license; check licensing before closed-source commercial use.
8. First model load downloads `yolo11n.pt` over the internet unless already cached. For a fully offline deployment, copy the model into the backend image and set `YOLO_MODEL` to its path.

## Suggested next iterations

- Add manual P1–P4 assignment at the first frame, track recovery and court ROI filtering.
- Add per-player heatmaps, timeline scrubbing with position overlay, and video preview calibration editing.
- Add durable queue and GPU acceleration.

## Credits

YOLO: https://github.com/ultralytics/ultralytics
ByteTrack: https://github.com/ifzhang/ByteTrack
OpenCV: https://github.com/opencv/opencv
FFmpeg: https://ffmpeg.org/


## Temporary storage and auto-deletion

- When processing completes, `expires_at` is set to the server's current Unix timestamp + `RESULT_TTL_SECONDS` (default 1800 seconds). Failed jobs also expire after 30 minutes.
- The frontend shows a countdown based on `expires_at`. Expiration is enforced by the backend independently of the browser.
- `POST /api/jobs/{id}/confirm-download` deletes files after explicit user confirmation. `DELETE /api/jobs/{id}` deletes a completed/failed job on demand. Both return `pending_downloads: true` if active response streams must finish first.
- A background cleanup thread scans every `CLEANUP_INTERVAL_SECONDS` (default 30). Expired files may remain on disk until active streams finish. Queued/processing jobs are not subject to the 30-minute result TTL; abandoned jobs older than `STALE_JOB_SECONDS` (default 86400) are cleaned up after restart.
- Do not trigger confirm-download merely from a link click: browsers cannot reliably confirm that the user saved a file.
- This MVP uses in-process locks and a single backend worker/process on one VPS. **Do not scale to multiple Uvicorn workers or multiple backend replicas** without replacing these locks with a shared job registry, distributed download leases and durable queue.
- File streaming here is sequential and does not implement HTTP Range requests; browser seeking in the video preview may be limited. For production, use a reverse proxy with protected file leases or a storage gateway with range support.
- Protect public endpoints with authentication and rate limits before deploying publicly. UUIDs are not authentication.

## Development checks

After installing backend dependencies, install the tracker and test dependencies:

```bash
cd backend
pip install lap==0.5.14 pytest httpx
python -m pytest tests -q
```

Build the frontend with `cd frontend && npm ci && npm run build`.
The retention tests cover expiration, manual deletion, active download protection,
abandoned-job recovery, original upload protection and CORS deletion requests.
AI accuracy still needs evaluation on representative pickleball match footage.
