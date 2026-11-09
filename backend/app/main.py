import json
import math
import os
import shutil
import threading
import uuid
import time
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .processor import process_video
from .options import AnalysisOptions
from pydantic import ValidationError

ROOT = Path(os.getenv('DATA_DIR', '/data'))
ROOT.mkdir(parents=True, exist_ok=True)
MAX_BYTES = int(os.getenv('MAX_UPLOAD_MB', '600')) * 1024 * 1024
TTL_SECONDS = int(os.getenv('RESULT_TTL_SECONDS', '1800'))
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL_SECONDS', '30'))
active_downloads = {}
pending_delete = set()
registry_lock = threading.RLock()
stop_cleanup = threading.Event()


def read_state(path):
    try:
        return json.loads((path / 'status.json').read_text())
    except (OSError, ValueError):
        return {}


def safe_remove(path):
    # Lock protects against new downloads starting while deletion begins.
    with registry_lock:
        key = str(path)
        if active_downloads.get(key, 0):
            pending_delete.add(key)
            return False
        pending_delete.add(key)
        shutil.rmtree(path, ignore_errors=True)
        pending_delete.discard(key)
        return True


def cleanup_once():
    now = time.time()
    for path in ROOT.iterdir():
        if not path.is_dir():
            continue
        state = read_state(path)
        if state.get('state') in ('complete', 'failed'):
            expires = state.get('expires_at')
            if expires is not None and now >= expires:
                safe_remove(path)
        elif state.get('state') in ('queued', 'processing'):
            # Recovery for abandoned jobs after a restart; never delete active workers.
            if now - state.get('created_at', now) > int(os.getenv('STALE_JOB_SECONDS', '86400')):
                with registry_lock:
                    if str(path) not in running_jobs:
                        safe_remove(path)


running_jobs = set()

def cleanup_loop():
    while not stop_cleanup.wait(CLEANUP_INTERVAL):
        try:
            cleanup_once()
        except Exception:
            import traceback
            traceback.print_exc()


@asynccontextmanager
async def lifespan(app):
    cleanup_once()
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    yield
    stop_cleanup.set()
    thread.join(timeout=2)


app = FastAPI(title='Pickleball Kun AI', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:8080').split(','), allow_credentials=False, allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['*'])
locks = {}


def job_dir(job_id):
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, 'Invalid job ID')
    path = ROOT / job_id
    if not path.is_dir():
        raise HTTPException(404, 'Job not found')
    return path


def update_status(path, **kwargs):
    f = path / 'status.json'
    with locks.setdefault(str(path), threading.Lock()):
        state = json.loads(f.read_text()) if f.exists() else {}
        state.update(kwargs)
        f.write_text(json.dumps(state))


def worker(path, corners, options=None):
    with registry_lock:
        running_jobs.add(str(path))
    try:
        update_status(path, state='processing', progress=0, message='Loading AI model')
        process_video(path / 'input.mp4', path, corners, lambda p, m: update_status(path, progress=p, message=m), options)
        update_status(path, state='complete', progress=100, message='Analysis ready', completed_at=time.time(), expires_at=time.time() + TTL_SECONDS)
    except Exception as exc:
        update_status(path, state='failed', message=str(exc)[:500], expires_at=time.time() + TTL_SECONDS)
    finally:
        with registry_lock:
            running_jobs.discard(str(path))


@app.get('/api/health')
def health():
    return {'ok': True}


@app.post('/api/jobs', status_code=202)
async def create_job(video: UploadFile = File(...), corners: str = Form(''), options: str = Form('{}')):
    if not (video.filename or '').lower().endswith('.mp4'):
        raise HTTPException(400, 'Upload an MP4 file')
    parsed = None
    if corners.strip():
        try:
            parsed = json.loads(corners)
            if not isinstance(parsed, list) or len(parsed) != 4 or any(not isinstance(p, list) or len(p) != 2 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 or v > 1 for v in p) for p in parsed):
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(400, 'corners must be four normalized [x,y] pairs: top-left, top-right, bottom-right, bottom-left')
    try:
        settings = AnalysisOptions.model_validate_json(options)
    except ValidationError as exc:
        await video.close()
        raise HTTPException(422, '; '.join(error['msg'] for error in exc.errors()))
    if settings.heatmap_overlay and parsed is None:
        await video.close()
        raise HTTPException(422, 'Chọn đủ 4 góc sân để chèn heatmap vào video.')
    if parsed is not None:
        import cv2
        import numpy as np
        polygon = np.array(parsed, dtype=np.float32)
        if not cv2.isContourConvex(polygon) or cv2.contourArea(polygon) < 0.005:
            await video.close()
            raise HTTPException(422, 'Bốn góc sân phải tạo thành tứ giác lồi, theo thứ tự trên trái, trên phải, dưới phải, dưới trái.')
    job_id = str(uuid.uuid4())
    path = ROOT / job_id
    path.mkdir()
    total = 0
    try:
        with (path / 'input.mp4').open('wb') as output:
            while chunk := await video.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(413, 'Video exceeds configured upload limit')
                output.write(chunk)
        update_status(path, id=job_id, state='queued', progress=0, message='Waiting to start', calibrated=parsed is not None, created_at=time.time(), options=settings.model_dump())
        threading.Thread(target=worker, args=(path, parsed, settings.model_dump()), daemon=True).start()
        return {'id': job_id}
    except Exception:
        shutil.rmtree(path, ignore_errors=True)
        raise
    finally:
        await video.close()


@app.get('/api/jobs/{job_id}')
def get_job(job_id: str):
    path = job_dir(job_id)
    state = read_state(path)
    if state.get('expires_at') and time.time() >= state['expires_at']:
        safe_remove(path)
        raise HTTPException(410, 'Job expired')
    return state


@app.get('/api/jobs/{job_id}/files/{filename}')
def get_file(job_id: str, filename: str):
    if filename not in {'annotated.mp4', 'heatmap.png', 'court.png', 'positions.json', 'summary.json', 'ball.json'}:
        raise HTTPException(404, 'File not found')
    path = job_dir(job_id)
    with registry_lock:
        state = read_state(path)
        if str(path) in pending_delete or (state.get('expires_at') and time.time() >= state['expires_at']):
            raise HTTPException(410, 'Job expired or deleted')
        target = path / filename
        if state.get('state') != 'complete' or not target.is_file():
            raise HTTPException(404, 'File not ready')
        key = str(path)
        active_downloads[key] = active_downloads.get(key, 0) + 1
    def chunks():
        try:
            with target.open('rb') as source:
                while chunk := source.read(1024 * 1024):
                    yield chunk
        finally:
            with registry_lock:
                active_downloads[key] -= 1
                if active_downloads[key] <= 0:
                    active_downloads.pop(key, None)
                    if key in pending_delete:
                        safe_remove(path)
    mime = {'mp4': 'video/mp4', 'png': 'image/png', 'json': 'application/json'}[filename.rsplit('.', 1)[-1]]
    return StreamingResponse(chunks(), media_type=mime, headers={'Content-Disposition': f'attachment; filename="{filename}"' if filename != 'annotated.mp4' else 'inline; filename="annotated.mp4"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@app.delete('/api/jobs/{job_id}', status_code=200)
def delete_job(job_id: str):
    path = job_dir(job_id)
    state = read_state(path)
    if state.get('state') in ('queued', 'processing'):
        raise HTTPException(409, 'Cannot delete a running job')
    deleted = safe_remove(path)
    return {'deleted': deleted, 'pending_downloads': not deleted}


@app.post('/api/jobs/{job_id}/confirm-download')
def confirm_download(job_id: str):
    # Called only after explicit user confirmation, not when download starts.
    return delete_job(job_id)
