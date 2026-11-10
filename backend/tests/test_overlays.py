import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main, processor
from app.options import AnalysisOptions
from app.overlays import COLORS, H, CourtOverlay, draw_fading_trail, draw_player


def observation(point=(100, 220)):
    return {'player': 'P1', 'name': 'Nguyễn An', 'box': [100, 50, 150, 190], 'court_xy': point}


def test_ellipse_replaces_the_box_and_preserves_unicode_name():
    frame = np.zeros((240, 320, 3), np.uint8)
    label = draw_player(frame, observation(), 'ellipse')
    assert label[2] == 'P1 · Nguyễn An'
    assert label[3] == COLORS[0]
    assert frame[180:201, 95:156].any()
    assert not frame[50:165, 100].any()
    box = np.zeros_like(frame)
    draw_player(box, observation(), 'box')
    assert box[80, 100].any()


def test_minimap_updates_positions_and_clears_missing_players():
    overlay = CourtOverlay(640, 480, [[0, 0], [1, 0], [1, 1], [0, 1]])
    first = np.zeros((480, 640, 3), np.uint8)
    overlay.update([observation()])
    overlay.draw_minimap(first, trails=False)
    left, top = overlay.position
    x, y = overlay.map_point((100, 220))
    assert tuple(first[top + y, left + x]) == COLORS[0][::-1]
    overlay.update([observation((300, 660))])
    moved = np.zeros_like(first)
    overlay.draw_minimap(moved, trails=False)
    assert not np.array_equal(first, moved)
    overlay.update([])
    empty = np.zeros_like(first)
    overlay.draw_minimap(empty)
    height, width = overlay.panel.shape[:2]
    assert np.array_equal(empty[top:top + height, left:left + width],
                          cv2.addWeighted(np.zeros_like(overlay.panel), .22, overlay.panel, .78, 0))
    assert not overlay.history['P1']


def test_minimap_keeps_off_court_positions_outside_the_boundary():
    overlay = CourtOverlay(640, 480, [[0, 0], [1, 0], [1, 1], [0, 1]])
    outside = overlay.map_point((-20, H / 2))
    boundary = overlay.map_point((0, H / 2))
    assert 0 <= outside[0] < boundary[0]


def test_perspective_lines_follow_selected_corners():
    corners = [[.2, .2], [.8, .25], [.9, .9], [.1, .8]]
    overlay = CourtOverlay(640, 480, corners)
    frame = np.zeros((480, 640, 3), np.uint8)
    overlay.draw_lines(frame)
    for x, y in corners:
        px, py = round(x * 640), round(y * 480)
        assert frame[py - 2:py + 3, px - 2:px + 3].any()
    assert not frame[:80].any()


@pytest.mark.parametrize('shape', [(48, 64), (128, 96), (240, 320)])
def test_minimap_fits_small_frames_or_skips_without_resizing_video(shape):
    height, width = shape
    frame = np.zeros((height, width, 3), np.uint8)
    overlay = CourtOverlay(width, height, [[0, 0], [1, 0], [1, 1], [0, 1]])
    overlay.update([observation()])
    overlay.draw_minimap(frame)
    assert frame.shape == (height, width, 3)


def test_trail_fades_and_never_bridges_missing_observations():
    frame = np.zeros((100, 200, 3), np.uint8)
    draw_fading_trail(frame, [(10, 30), (30, 30), None, (100, 30), (130, 30), (160, 30)], (235, 90, 235))
    assert frame[30, 150].sum() > frame[30, 20].sum() > 0
    assert not frame[25:36, 40:90].any()


@pytest.mark.parametrize('option', ['minimap_overlay', 'court_lines'])
def test_court_dependent_options_reject_upload_before_creating_a_job(tmp_path, monkeypatch, option):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    response = TestClient(main.app).post('/api/jobs', data={'options': json.dumps({option: True})},
                                         files={'video': ('test.mp4', b'fixture', 'video/mp4')})
    assert response.status_code == 422
    assert '4 góc sân' in response.json()['detail']
    assert not list(tmp_path.iterdir())


def test_invalid_marker_style_is_rejected():
    with pytest.raises(ValidationError):
        AnalysisOptions(player_marker='automatic')


def test_exports_with_all_graphics_keep_frame_data_and_selected_off_court_players(tmp_path, monkeypatch):
    source = tmp_path / 'input.mp4'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (320, 240))
    for index in range(6):
        frame = np.full((240, 320, 3), (45, 65, 45), np.uint8)
        cv2.circle(frame, (160 + index * 3, 100), 6, (0, 245, 245), -1)
        writer.write(frame)
    writer.release()
    def track(frame, **kwargs):
        assert int(frame[48, 64].max()) < 100
        boxes = SimpleNamespace(xyxy=torch.tensor([[50, 150, 100, 225], [220, 50, 270, 160]]), id=torch.tensor([11, 22]))
        return [SimpleNamespace(boxes=boxes)]
    monkeypatch.setattr(processor, 'YOLO', lambda *args: SimpleNamespace(track=track))
    output = tmp_path / 'output'
    output.mkdir()
    processor.process_video(source, output, [[.2, .2], [.8, .2], [.8, .7], [.2, .7]], lambda *args: None, {
        'player_count': 2, 'player_names': ['Nguyễn An', 'Trần Bình'],
        'player_seeds': [[75 / 320, 180 / 240], [245 / 320, 90 / 240]],
        'minimap_overlay': True, 'court_lines': True, 'heatmap_overlay': True,
        'minimap_ball_projection': True,
        'ball_tracking': True, 'ball_seed': [.5, 100 / 240],
    })
    positions = json.loads((output / 'positions.json').read_text())
    assert len(positions) == 6
    assert positions[0]['players'][0]['name'] == 'Nguyễn An'
    assert positions[0]['players'][0]['court_xy'][1] > H
    assert positions[1]['inferred'] is False
    assert positions[1]['players'] == positions[0]['players']
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['options']['player_marker'] == 'ellipse'
    assert summary['options']['minimap_overlay'] is True
    assert summary['options']['court_lines'] is True
    assert summary['ball_tracking']['detected_frames'] == 6
    assert len(json.loads((output / 'ball.json').read_text())['frames']) == 6
    assert summary['ball_tracking']['minimap_projection'] == 'image_homography_2d_approximate'
    ball_frames = json.loads((output / 'ball.json').read_text())['frames']
    assert all(abs(item['xy'][0] - (160 + index * 3)) <= 1 for index, item in enumerate(ball_frames))
    exported = cv2.VideoCapture(str(output / 'annotated.mp4'))
    assert exported.get(cv2.CAP_PROP_FRAME_COUNT) == 6
    ok, frame = exported.read()
    exported.release()
    assert ok and frame.shape == (240, 320, 3)
    assert frame[210, 15].max() < 60
    assert not np.array_equal(cv2.imread(str(output / 'heatmap.png')), cv2.imread(str(output / 'court.png')))
