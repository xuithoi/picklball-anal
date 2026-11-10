"""Video graphics derived from observed player positions and calibrated court geometry."""
from collections import defaultdict, deque
import math

import cv2
import numpy as np
from .calibration import validate_corners

W, H = 400, 880
# RGB, matching the P1-P4 selection markers in the frontend.
COLORS = [(213, 255, 112), (166, 149, 255), (255, 156, 112), (115, 216, 234)]


def court_segments():
    kitchen_top, kitchen_bottom = .5 - 7 / 44, .5 + 7 / 44
    return np.float32([
        [(0, 0), (1, 0)], [(1, 0), (1, 1)],
        [(1, 1), (0, 1)], [(0, 1), (0, 0)],
        [(0, .5), (1, .5)],
        [(0, kitchen_top), (1, kitchen_top)],
        [(0, kitchen_bottom), (1, kitchen_bottom)],
        [(.5, 0), (.5, kitchen_top)],
        [(.5, kitchen_bottom), (.5, 1)],
    ])


def draw_fading_trail(frame, points, color, thickness=2, glow=False):
    """Draw observations only; None explicitly breaks the trail."""
    points = list(points)
    segments = []
    for index in range(1, len(points)):
        previous, current = points[index - 1], points[index]
        if previous is None or current is None:
            continue
        strength = .2 + .8 * index / max(len(points) - 1, 1)
        faded = tuple(int(channel * strength) for channel in color)
        segments.append((tuple(map(int, previous)), tuple(map(int, current)), faded))
    # Paint all halos first so the next segment cannot cover the previous core.
    if glow:
        for previous, current, faded in segments:
            halo = tuple(int(channel * .2) for channel in faded)
            cv2.line(frame, previous, current, halo, thickness + 4, cv2.LINE_AA)
    for previous, current, faded in segments:
        cv2.line(frame, previous, current, faded, thickness, cv2.LINE_AA)


def draw_player(frame, observation, style, time_s=0, animated=True):
    slot = int(observation['player'][1:])
    color = COLORS[slot - 1][::-1]
    x1, y1, x2, y2 = map(int, observation['box'])
    if style == 'box':
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
    else:
        foot = ((x1 + x2) // 2, y2)
        radius = max(6, min(int((x2 - x1) * .55), max(6, frame.shape[1] // 10)))
        phase = time_s * 2 * math.pi * .9 + slot * .7
        if animated:
            radius = max(6, round(radius * (1 + .035 * math.sin(phase))))
        axes = (radius, max(3, int(radius * .24)))
        if animated:
            left, right = max(0, foot[0] - radius - 8), min(frame.shape[1], foot[0] + radius + 9)
            top, bottom = max(0, foot[1] - axes[1] - 8), min(frame.shape[0], foot[1] + axes[1] + 9)
            if right > left and bottom > top:
                halo = np.zeros((bottom - top, right - left, 3), dtype=np.uint8)
                cv2.ellipse(halo, (foot[0] - left, foot[1] - top), axes, 0, 0, 360, color, 4, cv2.LINE_AA)
                halo = cv2.GaussianBlur(halo, (0, 0), 2)
                roi = frame[top:bottom, left:right]
                cv2.addWeighted(roi, 1, halo, .5, 0, dst=roi)
        cv2.ellipse(frame, foot, axes, 0, 0, 360, (12, 20, 13), 5, cv2.LINE_AA)
        cv2.ellipse(frame, foot, axes, 0, 0, 360, color, 2, cv2.LINE_AA)
        inner = (max(3, int(axes[0] * .8)), max(2, int(axes[1] * .7)))
        cv2.ellipse(frame, foot, inner, 0, 0, 360, color, 1, cv2.LINE_AA)
        if animated:
            angle = (time_s * 120 + slot * 67) % 360
            orbit = (axes[0] + 4, axes[1] + 3)
            cv2.ellipse(frame, foot, orbit, 0, angle, angle + 60, color, 2, cv2.LINE_AA)
            end = math.radians(angle + 60)
            spark = (round(foot[0] + orbit[0] * math.cos(end)), round(foot[1] + orbit[1] * math.sin(end)))
            cv2.circle(frame, spark, 2, (240, 250, 245), -1, cv2.LINE_AA)
    name = observation['name']
    text = f"{observation['player']} · {name}" if name != observation['player'] else name
    return (x1, max(2, y1 - 28), text, COLORS[slot - 1])


class CourtOverlay:
    """Cache fixed geometry; update the small minimap only on inference frames."""
    def __init__(self, width, height, corners, trail_length=36, show_ball=False, court_orientation='top_bottom'):
        if court_orientation not in ('top_bottom', 'left_right'):
            raise ValueError('Invalid court orientation')
        self.projected_lines = None
        self.image_to_court = None
        self.show_ball = show_ball
        self.ball_history = deque(maxlen=trail_length)
        self.ball_current = None
        self.history = defaultdict(lambda: deque(maxlen=24))
        self.current = []
        self.panel = None
        if corners is None:
            return
        validate_corners(corners)
        source = np.float32([[x * width, y * height] for x, y in corners])
        # Keep clicked screen-corner order stable; rotate the physical court axis.
        # Image right edge becomes the far baseline for a sideways court.
        if court_orientation == 'left_right':
            source = np.roll(source, -1, axis=0)
        self.image_to_court = cv2.getPerspectiveTransform(
            source, np.float32([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]]))
        projection = cv2.getPerspectiveTransform(
            np.float32([[0, 0], [1, 0], [1, 1], [0, 1]]), source)
        projected = cv2.perspectiveTransform(court_segments().reshape(-1, 1, 2), projection)
        self.projected_lines = np.rint(projected.reshape(-1, 2, 2)).astype(np.int32)
        map_height = min(int(height * .32), 260)
        map_width = round(map_height * W / H)
        panel_width = max(92, map_width + 20)
        panel_height = map_height + 32 + (14 if show_ball else 0)
        if map_height < 70 or panel_width * 2 + 24 > width or panel_height + 16 > height:
            return
        self.origin = ((panel_width - map_width) // 2, 24)
        self.map_size = (map_width, map_height)
        self.position = (8, height - panel_height - 8)
        self.panel = np.full((panel_height, panel_width, 3), (20, 29, 24), dtype=np.uint8)
        cv2.rectangle(self.panel, (0, 0), (panel_width - 1, panel_height - 1), (83, 111, 91), 1)
        cv2.putText(self.panel, 'MINIMAP', (8, 15), cv2.FONT_HERSHEY_SIMPLEX,
                    .32, (200, 230, 211), 1, cv2.LINE_AA)
        lines = np.array([[self.map_point((x * (W - 1), y * (H - 1)))
                           for x, y in segment] for segment in court_segments()])
        for start, end in lines:
            cv2.line(self.panel, tuple(start), tuple(end), (112, 148, 127), 1, cv2.LINE_AA)
        for point in [(0, 0), (W - 1, 0), (W - 1, H - 1), (0, H - 1)]:
            cv2.circle(self.panel, self.map_point(point), 2, (191, 208, 198), -1, cv2.LINE_AA)
        if show_ball:
            cv2.putText(self.panel, 'BALL 2D', (8, panel_height - 6), cv2.FONT_HERSHEY_SIMPLEX,
                        .25, (235, 90, 235), 1, cv2.LINE_AA)

    def draw_lines(self, frame):
        if self.projected_lines is None:
            return
        for start, end in self.projected_lines:
            cv2.line(frame, tuple(start), tuple(end), (23, 39, 32), 4, cv2.LINE_AA)
            cv2.line(frame, tuple(start), tuple(end), (94, 240, 223), 2, cv2.LINE_AA)

    def update(self, observations):
        self.current = [item for item in observations if item['court_xy'] is not None]
        visible = {item['player'] for item in self.current}
        for player, history in self.history.items():
            if player not in visible:
                history.clear()
        for item in self.current:
            self.history[item['player']].append(item['court_xy'])

    def update_ball(self, point):
        self.ball_current = None
        if point is not None and self.image_to_court is not None:
            x, y = cv2.perspectiveTransform(np.float32([[point]]), self.image_to_court)[0, 0]
            # This is a 2D image projection, never a bounce/landing estimate.
            if np.isfinite([x, y]).all() and -.12 * W <= x <= 1.12 * W and -.12 * H <= y <= 1.12 * H:
                self.ball_current = (float(x), float(y))
        self.ball_history.append(self.ball_current)

    def map_point(self, point):
        x, y = point
        width, height = self.map_size
        return (self.origin[0] + round((x / (W - 1) + .12) / 1.24 * (width - 1)),
                self.origin[1] + round((y / (H - 1) + .12) / 1.24 * (height - 1)))

    def draw_minimap(self, frame, trails=True, time_s=0, animated=True):
        if self.panel is None:
            return
        left, top = self.position
        height, width = self.panel.shape[:2]
        panel = cv2.addWeighted(frame[top:top + height, left:left + width], .22, self.panel, .78, 0)
        if self.show_ball:
            path = [self.map_point(point) if point is not None else None for point in self.ball_history]
            draw_fading_trail(panel, path, (235, 90, 235), 1, glow=True)
        for item in self.current:
            slot = int(item['player'][1:])
            color = COLORS[slot - 1][::-1]
            if trails:
                draw_fading_trail(panel, [self.map_point(p) for p in self.history[item['player']]], color, 1)
            point = self.map_point(item['court_xy'])
            if animated:
                pulse = 5 + round(1 + math.sin(time_s * 2 * math.pi + slot * .7))
                cv2.circle(panel, point, pulse, tuple(int(c * .5) for c in color), 1, cv2.LINE_AA)
            cv2.circle(panel, point, 5, (10, 17, 13), -1, cv2.LINE_AA)
            cv2.circle(panel, point, 3, color, -1, cv2.LINE_AA)
            cv2.putText(panel, str(slot), (point[0] + 5, point[1] + 3),
                        cv2.FONT_HERSHEY_SIMPLEX, .28, color, 1, cv2.LINE_AA)
        if self.show_ball and self.ball_current is not None:
            point = self.map_point(self.ball_current)
            cv2.circle(panel, point, 4, (235, 90, 235), 1, cv2.LINE_AA)
            cv2.circle(panel, point, 2, (245, 225, 250), -1, cv2.LINE_AA)
        frame[top:top + height, left:left + width] = panel
