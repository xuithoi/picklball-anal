"""Render athlete names with a Unicode font rather than OpenCV's ASCII font."""
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=8)
def label_font(size):
    path = os.getenv('LABEL_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(path, size)


def draw_labels(frame, labels):
    if not labels:
        return frame
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    font = label_font(max(12, min(28, int(min(frame.shape[:2]) * .027))))
    for x, y, text, color in labels:
        # Fit long names to the frame without silently truncating the stored name.
        local_font = font
        while draw.textbbox((0, 0), text, font=local_font)[2] > image.width - 8 and local_font.size > 8:
            local_font = label_font(local_font.size - 1)
        box = draw.textbbox((0, 0), text, font=local_font)
        width, height = box[2] - box[0], box[3] - box[1]
        x = max(2, min(int(x), image.width - width - 6))
        y = max(2, min(int(y), image.height - height - 6))
        draw.rectangle((x - 2, y - 2, x + width + 3, y + height + 3), fill=(12, 20, 13))
        draw.text((x - box[0], y - box[1]), text, font=local_font, fill=tuple(color))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
