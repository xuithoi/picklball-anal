import asyncio
import json
import os
import tempfile
import time
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault('DATA_DIR', tempfile.mkdtemp(prefix='pickleball-tests-'))
from app import main


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    main.active_downloads.clear()
    main.pending_delete.clear()
    main.running_jobs.clear()
    yield
    main.active_downloads.clear()
    main.pending_delete.clear()
    main.running_jobs.clear()


def job(state='complete', expires=None, **extra):
    path = main.ROOT / str(uuid.uuid4())
    path.mkdir()
    (path / 'status.json').write_text(json.dumps({
        'state': state, 'expires_at': expires or time.time() + 1800, **extra,
    }))
    (path / 'positions.json').write_text('[{"player":"P1"}]')
    return path


def test_expired_job_removed_and_future_job_kept():
    expired = job(expires=time.time() - 1)
    future = job()
    main.cleanup_once()
    assert not expired.exists()
    assert future.exists()


def test_expired_status_denies_access():
    path = job(expires=time.time() - 1)
    with pytest.raises(HTTPException) as exc:
        main.get_job(path.name)
    assert exc.value.status_code == 410
    assert not path.exists()


def test_active_download_finishes_before_deletion():
    path = job()
    response = main.get_file(path.name, 'positions.json')
    assert main.delete_job(path.name) == {'deleted': False, 'pending_downloads': True}
    assert path.exists()
    with pytest.raises(HTTPException) as exc:
        main.get_file(path.name, 'positions.json')
    assert exc.value.status_code == 410

    async def consume():
        return b''.join([chunk async for chunk in response.body_iterator])

    assert asyncio.run(consume()) == b'[{"player":"P1"}]'
    assert not path.exists()
    assert not main.active_downloads


def test_running_jobs_cannot_be_deleted():
    path = job(state='processing')
    with pytest.raises(HTTPException) as exc:
        main.delete_job(path.name)
    assert exc.value.status_code == 409
    assert path.exists()


def test_stale_recovery_preserves_live_worker():
    abandoned = job(state='processing', created_at=time.time() - 90000)
    live = job(state='processing', created_at=time.time() - 90000)
    main.running_jobs.add(str(live))
    main.cleanup_once()
    assert not abandoned.exists()
    assert live.exists()


def test_confirm_download_deletes_files():
    path = job()
    client = TestClient(main.app)
    response = client.post(f'/api/jobs/{path.name}/confirm-download')
    assert response.status_code == 200
    assert response.json()['deleted'] is True
    assert not path.exists()


def test_original_upload_is_not_downloadable():
    path = job()
    client = TestClient(main.app)
    assert client.get(f'/api/jobs/{path.name}/files/input.mp4').status_code == 404


def test_cross_origin_delete_preflight():
    client = TestClient(main.app)
    response = client.options('/api/jobs/' + str(uuid.uuid4()), headers={
        'Origin': 'http://localhost:5173',
        'Access-Control-Request-Method': 'DELETE',
    })
    assert response.status_code == 200
    assert 'DELETE' in response.headers['access-control-allow-methods']
