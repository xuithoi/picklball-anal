import cv2
import numpy as np
import pytest

from app.ball import ColorBallTracker


def scene(center=(40, 80), radius=6, glare=False):
    frame = np.full((120, 160, 3), (55, 85, 55), np.uint8)
    cv2.circle(frame, center, radius, (0, 245, 245), -1)
    if glare:
        cv2.circle(frame, center, 2, (255, 255, 255), -1)
    return frame


def test_white_highlight_at_click_uses_surrounding_ball_color():
    frame = scene(glare=True)
    tracker = ColorBallTracker(frame, (40 / 160, 80 / 120), radius=6)
    assert np.linalg.norm(np.array(tracker.seed_xy) - (40, 80)) <= 1
    assert abs(tracker.color[0] - 30) <= 2
    point = tracker.update(scene((44, 80), glare=True))
    assert point is not None and abs(point[0] - 44) <= 1
    tracker.draw(frame, point)  # Estimated radius must remain drawable.


def test_slightly_missed_click_finds_small_ball_with_default_radius():
    tracker = ColorBallTracker(scene(radius=2), (43 / 160, 80 / 120), radius=6)
    assert 2 <= tracker.radius <= 3
    assert np.linalg.norm(np.array(tracker.seed_xy) - (40, 80)) <= 1
    point = tracker.update(scene((44, 80), radius=2))
    assert point is not None and abs(point[0] - 44) <= 1


def test_seed_near_image_boundary_is_safe():
    tracker = ColorBallTracker(scene((3, 3), radius=2), (0, 0), radius=6)
    assert np.linalg.norm(np.array(tracker.seed_xy) - (3, 3)) <= 1


@pytest.mark.parametrize('kind', ['court', 'white', 'distant', 'noise'])
def test_does_not_learn_uniform_court_white_ball_or_distant_distractors(kind):
    frame = np.full((120, 160, 3), (0, 180, 0) if kind == 'court' else (55, 85, 55), np.uint8)
    if kind == 'white': cv2.circle(frame, (40, 80), 6, (240, 240, 240), -1)
    if kind == 'distant': cv2.circle(frame, (80, 80), 6, (0, 245, 245), -1)
    if kind == 'noise': cv2.circle(frame, (40, 80), 1, (0, 245, 245), -1)
    with pytest.raises(ValueError, match='Phóng to ảnh'):
        ColorBallTracker(frame, (40 / 160, 80 / 120), radius=6)


def test_yellow_ball_separates_from_equally_bright_green_court():
    frame = np.full((120, 160, 3), (0, 245, 0), np.uint8)
    cv2.circle(frame, (40, 80), 6, (0, 245, 245), -1)
    tracker = ColorBallTracker(frame, (40 / 160, 80 / 120), radius=6)
    assert abs(tracker.color[0] - 30) <= 2
    assert np.linalg.norm(np.array(tracker.seed_xy) - (40, 80)) <= 1
