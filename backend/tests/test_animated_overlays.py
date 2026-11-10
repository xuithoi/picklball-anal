import copy

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main
from app.options import AnalysisOptions
from app.overlays import COLORS, H, W, CourtOverlay, draw_player


def person():
    return {'player': 'P1', 'name': 'An', 'box': [100, 40, 160, 180], 'court_xy': [100, 220]}


def render(time, animated=True, style='ellipse'):
    frame = np.full((240, 320, 3), (40, 65, 45), np.uint8)
    obs = person()
    original = copy.deepcopy(obs)
    draw_player(frame, obs, style, time, animated)
    assert obs == original
    return frame


def test_animation_is_deterministic_and_moves_without_changing_observations():
    first, later = render(0), render(.3)
    assert not np.array_equal(first, later)
    assert np.array_equal(first, render(0))
    assert np.array_equal(first[:150], later[:150])


@pytest.mark.parametrize('style,animated', [('ellipse', False), ('box', True)])
def test_static_or_box_style_does_not_animate(style, animated):
    assert np.array_equal(render(0, animated, style), render(.3, animated, style))


def test_animation_clips_safely_at_image_edges():
    frame = np.zeros((48, 64, 3), np.uint8)
    draw_player(frame, {'player': 'P4', 'name': 'Dũng', 'box': [-5, 3, 10, 48]}, 'ellipse', .25)
    assert frame.shape == (48, 64, 3)


def test_ball_projection_tracks_observations_and_keeps_missing_gaps():
    overlay = CourtOverlay(640, 480, [[0, 0], [1, 0], [1, 1], [0, 1]], show_ball=True)
    overlay.update_ball((320, 240))
    assert np.allclose(overlay.ball_current, ((W - 1) / 2, (H - 1) / 2))
    overlay.update_ball((330, 250))
    overlay.update_ball(None)
    assert overlay.ball_current is None
    overlay.update_ball((350, 270))
    assert overlay.ball_history[-2] is None
    frame = np.zeros((480, 640, 3), np.uint8)
    overlay.draw_minimap(frame, time_s=.5)
    assert frame.any()
    overlay.update_ball((-20000, -20000))
    assert overlay.ball_current is None and overlay.ball_history[-1] is None


def test_map_is_translucent_and_dots_keep_player_colors():
    overlay = CourtOverlay(640, 480, [[0, 0], [1, 0], [1, 1], [0, 1]])
    frame = np.full((480, 640, 3), (80, 120, 100), np.uint8)
    overlay.update([person()])
    overlay.draw_minimap(frame, time_s=.25)
    left, top = overlay.position
    assert not np.array_equal(frame[top + 1, left + 1], overlay.panel[1, 1])
    x, y = overlay.map_point((100, 220))
    assert tuple(frame[top + y, left + x]) == COLORS[0][::-1]


@pytest.mark.parametrize('options', [
    {'minimap_ball_projection': True},
    {'minimap_ball_projection': True, 'minimap_overlay': True},
    {'minimap_ball_projection': True, 'ball_tracking': True, 'ball_seed': [.5, .5]},
])
def test_ball_projection_requires_minimap_and_tracking(options):
    with pytest.raises(ValidationError, match='minimap'):
        AnalysisOptions.model_validate(options)


def test_ball_projection_without_corners_is_rejected_before_upload_job(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    response = TestClient(main.app).post('/api/jobs', data={'options': '{"minimap_ball_projection":true,"minimap_overlay":true,"ball_tracking":true,"ball_seed":[0.5,0.5]}'},
                                         files={'video': ('clip.mp4', b'fixture', 'video/mp4')})
    assert response.status_code == 422
    assert '4 góc sân' in response.json()['detail']
    assert not list(tmp_path.iterdir())
