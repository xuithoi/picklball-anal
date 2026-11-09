# Pickleball Kun AI — React + FastAPI + YOLO11 + ByteTrack

A runnable proof-of-concept for **offline processing of uploaded MP4 video**. Includes optional experimental ball color tracking initialized by selecting the ball on the first frame. No live camera, speed measurement or automatic scoring.

Deployment on Botkeep or Render: see [DEPLOY.md](DEPLOY.md) for the combined Docker image, resources, access password and persistent storage.

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
- `POST /api/jobs`: multipart `video` MP4, optional `corners` JSON (`[[x,y],...]`, normalized 0–1, convex TL/TR/BR/BL), and optional `options` JSON (see below)
- `GET /api/jobs/{id}`: status, progress, errors
- `GET /api/jobs/{id}/files/{filename}`: `annotated.mp4`, `heatmap.png`, `court.png`, `positions.json`, `summary.json`, `ball.json`

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
3. Heatmap counts detected player foot positions, not measured time in zones, and combines all four players. The court map displays the last detected positions. At inference stride 2, only every second frame is analyzed by default; the last player boxes remain visible on intermediate frames. The per-job inference stride is selectable (1–4).
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
The tests cover retention, request validation, option propagation, seeded ball tracking and loss/reacquisition, heatmap density, and video/JSON export (including NumPy detections).
AI accuracy still needs evaluation on representative pickleball match footage.

## Inputs and video overlays

The UI provides an original-video player, a fixed first-frame canvas, court-corner
selection, singles/doubles selection, person confidence, inference stride, and
checkboxes for player trails, heatmap inset and experimental ball tracking.

For the ball tracker, enable the option, choose **Chọn tâm bóng**, click the center
of the yellow/green ball on the first frame, and adjust the radius in source-video
pixels and hue tolerance. A bright saturated seed is required. The frame used for
selection is always frame zero, independent of the original-video playback position.

`options` is a multipart form field containing JSON. Defaults:

```json
{
  "player_count": 4,
  "confidence": 0.3,
  "inference_stride": 2,
  "player_marker": "ellipse",
  "player_trails": true,
  "minimap_overlay": false,
  "court_lines": false,
  "heatmap_overlay": false,
  "ball_tracking": false,
  "ball_seed": null,
  "ball_radius": 6,
  "ball_tolerance": 15
}
```

`player_count` must be 2 or 4, confidence 0.1–0.9, stride 1–4, ball radius 2–30 px,
and hue tolerance 5–40 OpenCV hue units. A ball seed is normalized `[x,y]` in `[0,1]`.
Ball tracking requires a seed; the heatmap video inset requires four valid court
corners. Invalid settings are rejected before a job is queued. Settings are recorded
in job status and `summary.json`.

The exported video includes colored foot rings (or optional bounding boxes), athlete
names, and, when selected, player movement trails,
a cumulative **player** heatmap inset, and an experimental yellow ball path. Ball
observations are made on every frame, independently of the person inference stride.
No ball position is interpolated through a missing detection. `ball.json` exports
video-pixel coordinates and timestamps, using `null` for missing observations.
`positions.json` includes every frame with an `inferred` flag; skipped frames retain
the most recent player detections and do not represent fresh model inference.

**Ball tracking is a seeded color/shape heuristic, not a trained pickleball model.**
Similar colors, motion blur, fast movement, camera changes, white balls or occlusion
can cause false or missing observations. The reported observed-frame coverage is
not an accuracy score. Real-match accuracy has not been validated. A dedicated ball
model and annotated pickleball footage are needed for reliable automatic detection.

The PNG heatmap counts accumulated player observations (not ball landings or time
spent in seconds). Repeated visits add density. Ball image coordinates are not
projected onto the court because an airborne ball violates the planar assumption.

Brand asset: `frontend/public/brand/kun-logo.png` (transparent PNG), used in the
header, footer and favicon. The homepage demo is explicitly simulated data.

## Athlete names

Enter names for P1–P4, or P1–P2 in singles mode. Names are optional, trimmed,
limited to 40 characters, and support Vietnamese Unicode; blank entries keep the
P-number. The multipart `options.player_names` array must contain exactly
`player_count` entries when supplied. Names appear in the video, court PNG,
per-frame player observations (`name`) and summary roster (`players`).

After entering names, use the P1–P4 (or P1–P2) selection buttons to click the
middle of each corresponding athlete's torso on the uploaded video's first frame.
Select every athlete when supplying names or positions. Court-corner numbers are
separate from athlete labels. Names are entered by the user, never inferred from
the demo or recognized automatically.

The optional `options.player_seeds` is an array of normalized `[x,y]` points in
roster order, with exactly `player_count` distinct entries. The backend binds each
point to a distinct person detection containing it on the first frame. It rejects
unmatched positions rather than assigning names by detection order. Later unknown
tracker IDs are ignored when manual assignments are supplied. Without positions,
API clients retain the original detection-order behavior. Tracking can still switch
IDs during occlusion; identity recovery and team recognition are not implemented.

The frontend checks `/api/health` before uploading video and reports an actionable
error for empty, HTML, malformed, or unexpected JSON responses. Cloudflare static
asset hosting serves only the frontend: `/api/*` must reach the FastAPI backend to
process videos. Vite's development proxy does not configure production routing.
Frontend API response regression checks: `cd frontend && node --test src/api.test.js`.
Unicode overlays use DejaVu Sans (`fonts-dejavu-core` in the Docker image). Native
installs require `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`, or set `LABEL_FONT`
to an existing Unicode TrueType font path.


## Video court graphics

The default player marker is a double ellipse at the detected foot position.
Uncheck **Vòng màu dưới chân** to use bounding boxes instead. Marker colors match
the P1–P4 name/position selectors. Names still come from user input and first-frame
manual assignments; the renderer does not recognize athlete identity.

Enable **Minimap trong video** for a frame-updated player map at the bottom left,
and **Vạch sân trên video** for projected boundaries, kitchen lines, center service
lines and net reference. Both require four selected court corners, in the existing
TL/TR/BR/BL order. The minimap and optional density heatmap occupy opposite corners.
The minimap represents player ground positions; airborne ball positions are not
projected onto the court. Very small videos skip an inset that would not fit.

API options: `player_marker` is `ellipse` (default) or `box`; `minimap_overlay` and
`court_lines` default to false. These options are saved in job status and summary.
A manually assigned athlete remains labeled outside the court boundary. Exported
`court_xy` values are in the 400×880 court coordinate system and may fall outside
that rectangle; they are not clamped to the baseline. The minimap includes a small
surrounding margin. Only on-court observations contribute to the heatmap.

Player and ball trails fade toward older observations. Ball trails are magenta,
retain explicit gaps for missing detections and are limited to approximately
0.7 seconds (4–90 frames). They do not add synthetic observations or change the
exported ball positions. The existing seeded color tracker is still experimental;
this change does not add a trained ball detector, hit/bounce detection or 3D tracking.

Deployment order: update/rebuild the EC2 backend from this feature branch before
rolling out the frontend. An older backend rejects the new option names. Merging
or deploying Cloudflare alone does not update the Python container on EC2.
