"""Experimental seed-based color tracking; this is not a trained ball detector."""
from collections import deque

import cv2
import numpy as np

from .overlays import draw_fading_trail


class ColorBallTracker:
    def __init__(self, first_frame, seed, radius=6, tolerance=15, trail_length=36):
        height, width = first_frame.shape[:2]
        self.tolerance = tolerance
        click = np.array([min(width - 1, seed[0] * width), min(height - 1, seed[1] * height)], dtype=float)
        span = max(6, int(np.ceil(radius * 2.5)))
        x0, y0 = max(0, int(click[0]) - span), max(0, int(click[1]) - span)
        x1, y1 = min(width, int(click[0]) + span + 1), min(height, int(click[1]) + span + 1)
        hsv = cv2.cvtColor(first_frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
        yellow_green = (hsv[:, :, 0] >= 15) & (hsv[:, :, 0] <= 90) & (hsv[:, :, 1] >= 60)
        contrast = min(255, max(90, float(np.median(hsv[:, :, 2])) + 20))
        candidates = []
        # Try local brightness contrast before the more permissive color pass.
        for brightness in [contrast, max(90, float(np.median(hsv[:, :, 2])) + 5), 90]:
            mask = (yellow_green & (hsv[:, :, 2] >= brightness)).astype(np.uint8) * 255
            contours = []
            for low, high in [(15, 45), (45, 91)]:
                band = mask.copy()
                band[(hsv[:, :, 0] < low) | (hsv[:, :, 0] >= high)] = 0
                found, _ = cv2.findContours(band, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contours.extend(found)
            for contour in contours:
                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)
                if area < 2 or area > np.pi * radius ** 2 * 4 or not perimeter:
                    continue
                if 4 * np.pi * area / perimeter ** 2 < .35:
                    continue
                (cx, cy), detected_radius = cv2.minEnclosingCircle(contour)
                center = np.array([cx + x0, cy + y0])
                distance = np.linalg.norm(center - click)
                if detected_radius < 1.5 or detected_radius > max(4, radius * 2) or distance > max(4, radius * 1.25):
                    continue
                blob = np.zeros_like(mask)
                cv2.drawContours(blob, [contour], -1, 255, -1)
                pixels = hsv[(blob != 0) & (mask != 0)]
                if len(pixels) < 3:
                    continue
                # Median excludes a white highlight or dark pixel at the click.
                color = np.median(pixels, axis=0).astype(float)
                candidates.append((distance, center, detected_radius, color))
            if candidates:
                break
        if not candidates:
            raise ValueError('Không thấy bóng vàng/xanh đủ rõ quanh điểm đã chọn. Phóng to ảnh, chỉnh tâm và bán kính hoặc chọn khung hình khác. Bóng trắng hoặc bị che khuất chưa được hỗ trợ.')
        _, self.last, detected_radius, self.color = min(candidates, key=lambda item: item[0])
        self.radius = float(np.clip(detected_radius, 2, 30))
        self.seed_xy = tuple(map(float, self.last))
        self.velocity = np.zeros(2)
        self.missing = 0
        self.path = deque(maxlen=trail_length)

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
        color = (235, 90, 235)
        draw_fading_trail(frame, self.path, color, 2)
        if point is not None:
            cv2.circle(frame, point, int(round(self.radius)) + 4, color, 2, cv2.LINE_AA)
            cv2.circle(frame, point, 2, (240, 250, 250), -1, cv2.LINE_AA)
            cv2.putText(frame, 'BALL / EXP', (point[0] + 10, max(16, point[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1, cv2.LINE_AA)
