import json
import time
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import main
from app.ball import ColorBallTracker
from app.options import AnalysisOptions
from app.processor import heatmap_image, draw_court


def frame(ball=None):
    image = np.full((240, 320, 3), (65, 80, 40), dtype=np.uint8)
    if ball is not None:
        cv2.circle(image, ball, 6, (0, 240, 240), -1)
    return image


def test_ball_follows_movement_and_reports_occlusion():
    tracker = ColorBallTracker(frame((40, 80)), (40/320, 80/240), 6)
    for x in range(40, 121, 8):
        point = tracker.update(frame((x, 80)))
        assert point is not None
        assert abs(point[0] - x) <= 1
    assert tracker.update(frame()) is None
    assert tracker.path[-1] is None
    point = tracker.update(frame((132, 80)))
    assert point is not None
    assert abs(point[0] - 132) <= 1
    assert tracker.path[-2] is None


def test_tracker_rejects_bad_seed_and_large_same_color_distractor():
    tracker = ColorBallTracker(frame((40, 80)), (40/320, 80/240), 6)
    image = frame()
    cv2.rectangle(image, (20, 30), (120, 170), (0, 240, 240), -1)
    assert tracker.update(image) is None
    with pytest.raises(ValueError):
        ColorBallTracker(np.zeros_like(image), (.5, .5))


@pytest.mark.parametrize('options', [
    {'ball_tracking': True}, {'confidence': 2}, {'player_count': 3},
    {'ball_seed': [-.1, .5]}, {'inference_stride': 0}, {'ball_radius': 0},
    {'confidence': float('nan')}, {'unknown': True},
])
def test_invalid_options(options):
    with pytest.raises(ValidationError):
        AnalysisOptions.model_validate(options)


@pytest.mark.parametrize('payload', [
    {'options': json.dumps({'ball_tracking': True})},
    {'options': json.dumps({'heatmap_overlay': True})},
    {'options': '[]'},
    {'corners': '[[0,0],[0,0],[0,0],[0,0]]'},
    {'corners': '[[0,0],[1,1],[1,0],[0,1]]'},
    {'corners': '[[NaN,0],[1,0],[1,1],[0,1]]'},
])
def test_invalid_requests_do_not_create_jobs(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    response = TestClient(main.app).post('/api/jobs', data=payload, files={'video': ('test.mp4', b'invalid', 'video/mp4')})
    assert response.status_code in (400, 422)
    assert not list(tmp_path.iterdir())


def test_options_reach_worker_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    captured = []
    def process(input_file, path, corners, progress, options):
        captured.append((corners, options))
    monkeypatch.setattr(main, 'process_video', process)
    settings = {'player_count': 2, 'confidence': .65, 'player_trails': False, 'heatmap_overlay': True}
    response = TestClient(main.app).post('/api/jobs', data={
        'options': json.dumps(settings), 'corners': '[[0,0],[1,0],[1,1],[0,1]]',
    }, files={'video': ('test.mp4', b'fixture', 'video/mp4')})
    assert response.status_code == 202
    job_id = response.json()['id']
    for _ in range(100):
        state = main.get_job(job_id)
        if state.get('state') == 'complete':
            break
        time.sleep(.01)
    assert state['state'] == 'complete'
    assert captured[0][1]['player_count'] == 2
    assert captured[0][1]['confidence'] == .65
    assert captured[0][1]['heatmap_overlay'] is True
    assert state['options']['player_trails'] is False


def test_heatmap_reflects_repeated_visits():
    heat = np.zeros((880, 400), dtype=np.float32)
    heat[300, 100] += 1
    heat[300, 300] += 3
    rendered = heatmap_image(heat, draw_court())
    assert not np.array_equal(rendered[300, 100], rendered[300, 300])


def test_processor_exports_numpy_detections_and_all_frames(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import torch
    from app import processor
    source = tmp_path / 'test.mp4'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (96, 128))
    for i in range(4):
        writer.write(np.full((128, 96, 3), 50 + i * 10, dtype=np.uint8))
    writer.release()
    result = SimpleNamespace(boxes=SimpleNamespace(xyxy=torch.tensor([[10.5, 15.25, 40.75, 90.5]]), id=torch.tensor([1])))
    fake_model = SimpleNamespace(track=lambda *args, **kwargs: [result])
    monkeypatch.setattr(processor, 'YOLO', lambda *args: fake_model)
    output = tmp_path / 'output'
    output.mkdir()
    processor.process_video(source, output, [[0,0],[1,0],[1,1],[0,1]], lambda *args: None, {'heatmap_overlay': True, 'player_names': ['Nguyễn Ánh', 'Trần Bình', 'Lê Cường', 'Đỗ Dũng']})
    positions = json.loads((output / 'positions.json').read_text())
    assert len(positions) == 4
    assert positions[0]['players'][0]['box'] == [10.5, 15.2, 40.8, 90.5]
    assert positions[0]['players'][0]['name'] == 'Nguyễn Ánh'
    assert json.loads((output / 'summary.json').read_text())['players'][0] == {'player': 'P1', 'name': 'Nguyễn Ánh'}
    assert positions[1]['inferred'] is False
    assert positions[1]['players']
    assert json.loads((output / 'summary.json').read_text())['tracked_players'] == 1
    assert (output / 'annotated.mp4').stat().st_size > 0


def test_athlete_names_trim_normalize_and_fallback():
    settings = AnalysisOptions(player_count=2, player_names=['  Nguyễn Ánh  ', ' '])
    assert settings.player_names == ['Nguyễn Ánh', 'P2']
    assert AnalysisOptions(player_count=4).player_names == ['P1', 'P2', 'P3', 'P4']


@pytest.mark.parametrize('names', [['A'], ['A', 'B', 'C'], ['A' * 41, 'B'], ['A\nB', 'C']])
def test_invalid_athlete_names(names):
    with pytest.raises(ValidationError):
        AnalysisOptions(player_count=2, player_names=names)
