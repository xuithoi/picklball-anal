import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from app import main, processor
from app.calibration import validate_corners, visible_foot
from app.overlays import CourtOverlay, COLORS, W, H

CORNERS = [[.3, .1], [.75, .14], [.9, .9], [.1, .85]]
WRONG_ORDERS = [CORNERS[i:] + CORNERS[:i] for i in range(1, 4)] + [list(reversed(CORNERS[i:] + CORNERS[:i])) for i in range(4)]


@pytest.mark.parametrize('corners', WRONG_ORDERS)
def test_convex_but_wrong_corner_order_rejected_before_job(corners, tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    response = TestClient(main.app).post('/api/jobs', data={'corners': json.dumps(corners)}, files={'video': ('clip.mp4', b'fixture', 'video/mp4')})
    assert response.status_code == 422
    assert 'trên trái' in response.json()['detail']
    assert not list(tmp_path.iterdir())


def test_near_left_and_mid_right_player_feet_keep_minimap_sides():
    validate_corners(CORNERS)
    width, height = 900, 570
    overlay = CourtOverlay(width, height, CORNERS)
    inverse = np.linalg.inv(overlay.image_to_court)
    expected = np.float32([[[40, 810]], [[340, 520]]])
    feet = cv2.perspectiveTransform(expected, inverse).reshape(-1, 2)
    observations = []
    for slot, (x, y) in enumerate(feet, 1):
        box = [x - 20, y - 95, x + 20, y]
        foot = visible_foot(box, height)
        point = cv2.perspectiveTransform(np.float32([[foot]]), overlay.image_to_court)[0, 0]
        observations.append({'player': f'P{slot}', 'court_xy': point})
        assert np.allclose(point, expected[slot-1, 0], atol=.001)
    overlay.update(observations)
    frame = np.zeros((height, width, 3), np.uint8)
    overlay.draw_minimap(frame, trails=False, animated=False)
    left, top = overlay.position
    p1, p2 = [overlay.map_point(item['court_xy']) for item in observations]
    assert p1[0] < p2[0] and p1[1] > p2[1]
    for slot, (x, y) in enumerate([p1, p2]):
        assert tuple(frame[top+y, left+x]) == COLORS[slot][::-1]


@pytest.mark.parametrize('box', [[10, 20, 50, 240], [10, 20, 50, 239.5], [10, 20, 50, float('nan')]])
def test_missing_feet_are_not_used_as_ground_positions(box):
    assert visible_foot(box, 240) is None


def test_clipped_player_keeps_name_but_has_no_map_position(tmp_path, monkeypatch):
    source = tmp_path / 'clip.mp4'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (320, 240))
    for _ in range(4):
        writer.write(np.zeros((240, 320, 3), np.uint8))
    writer.release()
    boxes = SimpleNamespace(xyxy=torch.tensor([[30, 170, 70, 240], [220, 50, 270, 160]]), id=torch.tensor([11, 22]))
    monkeypatch.setattr(processor, 'YOLO', lambda *a: SimpleNamespace(track=lambda *a, **kw: [SimpleNamespace(boxes=boxes)]))
    output = tmp_path / 'out'; output.mkdir()
    processor.process_video(source, output, [[0, 0], [1, 0], [1, 1], [0, 1]], lambda *a: None, {
        'player_count': 2, 'player_names': ['An', 'Bình'], 'player_seeds': [[.15, .85], [.75, .3]], 'minimap_overlay': True,
    })
    frames = json.loads((output / 'positions.json').read_text())
    for frame in frames:
        p1, p2 = frame['players']
        assert p1['name'] == 'An' and p1['court_xy'] is None and p1['foot_xy'] is None
        assert p1['projection_status'] == 'feet_out_of_frame'
        assert p2['court_xy'] is not None and p2['projection_status'] == 'calibrated'
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['calibration']['corners_normalized'] == [[0, 0], [1, 0], [1, 1], [0, 1]]
    assert summary['calibration']['clipped_feet_observations'] == 2
    assert any('cắt chân' in warning for warning in summary['warnings'])
