import json
import subprocess
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main, processor
from app.options import AnalysisOptions
from app.video import TimestampDecoder


def make_video(path, fps=10, frames=10):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (320, 240))
    for index in range(frames):
        frame = np.full((240, 320, 3), 20 + index * 15, np.uint8)
        if index >= 5:
            cv2.circle(frame, (160 + (index - 5) * 8, 100), 6, (0, 245, 245), -1)
        writer.write(frame)
    writer.release()


@pytest.mark.parametrize('start', [-1, float('nan'), float('inf')])
def test_invalid_start_time(start):
    with pytest.raises(ValidationError):
        AnalysisOptions(start_time_s=start)


@pytest.mark.parametrize('start', [.5, .499999])
def test_seeds_and_tracking_initialize_from_selected_frame_and_exports_restart_at_zero(tmp_path, monkeypatch, start):
    source = tmp_path / 'source.mp4'
    make_video(source)
    def track(frame, **kwargs):
        assert 85 <= frame[10, 10].mean() <= 165
        return [SimpleNamespace(boxes=SimpleNamespace(
            id=torch.tensor([10, 20]), xyxy=torch.tensor([[40, 30, 90, 200], [220, 40, 270, 200]])))]
    monkeypatch.setattr(processor, 'YOLO', lambda *args: SimpleNamespace(track=track))
    out = tmp_path / 'out'
    out.mkdir()
    processor.process_video(source, out, None, lambda *args: None, {
        'start_time_s': start, 'player_count': 2, 'player_names': ['An', 'Bình'],
        'player_seeds': [[65 / 320, .4], [245 / 320, .4]],
        'ball_tracking': True, 'ball_seed': [.5, 100 / 240],
    })
    summary = json.loads((out / 'summary.json').read_text())
    positions = json.loads((out / 'positions.json').read_text())
    ball = json.loads((out / 'ball.json').read_text())
    assert summary['frames'] == 5
    assert summary['start_time_s'] == start
    assert summary['duration_s'] == .5
    assert summary['timeline'] == 'output_relative'
    assert positions[0]['time_s'] == ball['frames'][0]['time_s'] == 0
    assert positions[-1]['time_s'] == .4
    assert positions[0]['players'][0]['name'] == 'An'
    assert summary['ball_tracking']['detected_frames'] == 5
    assert abs(ball['frames'][0]['xy'][0] - 160) <= 1
    cap = cv2.VideoCapture(str(out / 'annotated.mp4'))
    assert cap.get(cv2.CAP_PROP_FRAME_COUNT) == 5
    cap.release()


@pytest.mark.parametrize('fps,frame_index', [(30, 1), (60, 1), (25, 2)])
def test_fractional_timestamp_retains_the_displayed_frame(tmp_path, fps, frame_index):
    source = tmp_path / 'source.mp4'
    make_video(source, fps=fps)
    # Mirrors the microsecond floor applied to requestVideoFrameCallback.mediaTime.
    start = np.floor(frame_index / fps * 1e6) / 1e6
    decoder = TimestampDecoder(source, start, 320, 240)
    try:
        ok, frame = decoder.read()
        assert ok
        assert abs(frame[10, 10].mean() - (20 + frame_index * 15)) < 6
        count = 1
        while decoder.read()[0]:
            count += 1
        assert count == 10 - frame_index
    finally:
        decoder.close()


def test_timestamp_decode_handles_variable_frame_rate(tmp_path):
    lines = []
    for index, duration in enumerate([.08, .4, .12, .28]):
        image = tmp_path / f'{index}.png'
        cv2.imwrite(str(image), np.full((120, 160, 3), 20 + 40 * index, np.uint8))
        lines.extend([f"file '{image}'", f'duration {duration}'])
    lines.append(f"file '{tmp_path / '3.png'}'")
    concat = tmp_path / 'frames.txt'
    concat.write_text('\n'.join(lines))
    source = tmp_path / 'vfr.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                    '-i', str(concat), '-fps_mode', 'vfr', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'frame=best_effort_timestamp_time', '-of', 'json', str(source)], check=True, capture_output=True, text=True)
    frames = json.loads(probe.stdout)['frames']
    selected_time = float(frames[2]['best_effort_timestamp_time'])
    decoder = TimestampDecoder(source, selected_time, 160, 120)
    try:
        ok, frame = decoder.read()
        assert ok and abs(frame.mean() - 100) < 6
        remaining = 1
        while decoder.read()[0]:
            remaining += 1
        assert remaining == len(frames) - 2
    finally:
        decoder.close()


def test_start_at_end_is_rejected_before_model_loading(tmp_path, monkeypatch):
    source = tmp_path / 'source.mp4'
    make_video(source)
    monkeypatch.setattr(processor, 'YOLO', lambda *args: pytest.fail('Model should not load'))
    with pytest.raises(ValueError, match='kết thúc'):
        processor.process_video(source, tmp_path, None, lambda *args: None, {'start_time_s': 1})


def test_start_time_reaches_worker_and_job_status(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    captured = []
    monkeypatch.setattr(main, 'process_video', lambda source, path, corners, progress, options: captured.append(options))
    response = TestClient(main.app).post('/api/jobs', data={'options': '{"start_time_s":0.5}'},
                                         files={'video': ('test.mp4', b'fixture', 'video/mp4')})
    assert response.status_code == 202
    for _ in range(100):
        state = main.get_job(response.json()['id'])
        if state.get('state') == 'complete': break
        time.sleep(.01)
    assert state['state'] == 'complete'
    assert state['options']['start_time_s'] == captured[0]['start_time_s'] == .5
