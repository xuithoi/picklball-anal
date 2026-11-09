"""Video graphics derived from observed player positions and calibrated court geometry."""
from collections import defaultdict, deque

import cv2
import numpy as np

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


def draw_fading_trail(frame, points, color, thickness=2):
    """Draw observations only; None explicitly breaks the trail."""
    points = list(points)
    for index in range(1, len(points)):
        previous, current = points[index - 1], points[index]
        if previous is None or current is None:
            continue
        strength = .2 + .8 * index / max(len(points) - 1, 1)
        faded = tuple(int(channel * strength) for channel in color)
        cv2.line(frame, tuple(map(int, previous)), tuple(map(int, current)),
                 faded, thickness, cv2.LINE_AA)


def draw_player(frame, observation, style):
    slot = int(observation['player'][1:])
    color = COLORS[slot - 1][::-1]
    x1, y1, x2, y2 = map(int, observation['box'])
    if style == 'box':
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
    else:
        foot = ((x1 + x2) // 2, y2)
        radius = max(6, min(int((x2 - x1) * .55), max(6, frame.shape[1] // 10)))
        axes = (radius, max(3, int(radius * .24)))
        cv2.ellipse(frame, foot, axes, 0, 0, 360, (12, 20, 13), 5, cv2.LINE_AA)
        cv2.ellipse(frame, foot, axes, 0, 0, 360, color, 2, cv2.LINE_AA)
        inner = (max(3, int(axes[0] * .8)), max(2, int(axes[1] * .7)))
        cv2.ellipse(frame, foot, inner, 0, 0, 360, color, 1, cv2.LINE_AA)
    name = observation['name']
    text = f"{observation['player']} · {name}" if name != observation['player'] else name
    return (x1, max(2, y1 - 28), text, COLORS[slot - 1])


class CourtOverlay:
    """Cache fixed geometry; update the small minimap only on inference frames."""
    def __init__(self, width, height, corners):
        self.projected_lines = None
        self.history = defaultdict(lambda: deque(maxlen=24))
        self.current = []
        self.panel = None
        if corners is None:
            return
        source = np.float32([[x * width, y * height] for x, y in corners])
        projection = cv2.getPerspectiveTransform(
            np.float32([[0, 0], [1, 0], [1, 1], [0, 1]]), source)
        projected = cv2.perspectiveTransform(court_segments().reshape(-1, 1, 2), projection)
        self.projected_lines = np.rint(projected.reshape(-1, 2, 2)).astype(np.int32)
        map_height = min(int(height * .38), 300)
        map_width = round(map_height * W / H)
        panel_width = max(92, map_width + 20)
        panel_height = map_height + 32
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

    def map_point(self, point):
        x, y = point
        width, height = self.map_size
        return (self.origin[0] + round((x / (W - 1) + .12) / 1.24 * (width - 1)),
                self.origin[1] + round((y / (H - 1) + .12) / 1.24 * (height - 1)))

    def draw_minimap(self, frame, trails=True):
        if self.panel is None:
            return
        panel = self.panel.copy()
        for item in self.current:
            slot = int(item['player'][1:])
            color = COLORS[slot - 1][::-1]
            if trails:
                draw_fading_trail(panel, [self.map_point(p) for p in self.history[item['player']]], color, 1)
            point = self.map_point(item['court_xy'])
            cv2.circle(panel, point, 5, (10, 17, 13), -1, cv2.LINE_AA)
            cv2.circle(panel, point, 3, color, -1, cv2.LINE_AA)
            cv2.putText(panel, str(slot), (point[0] + 5, point[1] + 3),
                        cv2.FONT_HERSHEY_SIMPLEX, .28, color, 1, cv2.LINE_AA)
        left, top = self.position
        height, width = panel.shape[:2]
        frame[top:top + height, left:left + width] = panel
