"""Experimental seed-based color tracking; this is not a trained ball detector."""
from collections import deque

import cv2
import numpy as np


class ColorBallTracker:
    def __init__(self, first_frame, seed, radius=6, tolerance=15):
        height, width = first_frame.shape[:2]
        self.radius = radius
        self.tolerance = tolerance
        self.last = np.array([min(width - 1, seed[0] * width), min(height - 1, seed[1] * height)], dtype=float)
        x, y = np.rint(self.last).astype(int)
        hsv = cv2.cvtColor(first_frame, cv2.COLOR_BGR2HSV)
        self.color = hsv[y, x].astype(float)
        if self.color[1] < 40 or self.color[2] < 40:
            raise ValueError('Chọn lại tâm bóng màu vàng/xanh sáng ở khung hình đầu. Chế độ thử nghiệm chưa phù hợp bóng trắng hoặc bóng bị che khuất.')
        self.velocity = np.zeros(2)
        self.missing = 0
        self.path = deque(maxlen=36)

    def update(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue_distance = np.abs(hsv[:, :, 0].astype(float) - self.color[0])
        hue_distance = np.minimum(hue_distance, 180 - hue_distance)
        mask = ((hue_distance <= self.tolerance) &
                (hsv[:, :, 1] >= max(40, self.color[1] - 100)) &
                (hsv[:, :, 2] >= max(40, self.color[2] - 100))).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        search = max(self.radius * 12, frame.shape[1] * .10) * (1 + min(self.missing, 6) * .25)
        predicted = self.last + self.velocity * min(self.missing + 1, 3)
        candidates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if not np.pi * self.radius ** 2 * .15 <= area <= np.pi * self.radius ** 2 * 4:
                continue
            perimeter = cv2.arcLength(contour, True)
            if not perimeter or 4 * np.pi * area / perimeter ** 2 < .3:
                continue
            (x, y), radius = cv2.minEnclosingCircle(contour)
            distance = np.linalg.norm(np.array([x, y]) - predicted)
            if distance <= search:
                candidates.append((distance + abs(radius - self.radius) * 2, np.array([x, y])))
        if not candidates:
            self.missing += 1
            # Never draw an invented segment across frames with no observation.
            self.path.append(None)
            if self.missing >= 3:
                self.velocity[:] = 0
            return None
        _, position = min(candidates, key=lambda candidate: candidate[0])
        self.velocity = (position - self.last) if self.missing == 0 else np.zeros(2)
        self.last = position
        self.missing = 0
        point = tuple(np.rint(position).astype(int))
        self.path.append(point)
        return point

    def draw(self, frame, point):
        previous = None
        for current in self.path:
            if previous is not None and current is not None:
                cv2.line(frame, previous, current, (70, 245, 255), 2, cv2.LINE_AA)
            previous = current
        if point is not None:
            cv2.circle(frame, point, self.radius + 4, (70, 245, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, 'BALL / EXP', (point[0] + 10, max(16, point[1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, .4, (70, 245, 255), 1, cv2.LINE_AA)
