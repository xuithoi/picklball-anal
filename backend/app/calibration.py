"""Court calibration follows image TL, TR, BR, BL, never click order alone."""
import cv2
import numpy as np

CORNER_ERROR = ('Chọn lại 4 góc ngoài của toàn sân theo thứ tự: trên trái → trên phải → '
                'dưới phải → dưới trái. Không chọn góc vùng bếp hoặc góc lưới.')


def validate_corners(corners):
    polygon = np.asarray(corners, dtype=np.float32)
    if polygon.shape != (4, 2) or not np.isfinite(polygon).all() or (polygon < 0).any() or (polygon > 1).any():
        raise ValueError(CORNER_ERROR)
    tl, tr, br, bl = polygon
    # Convexity alone also accepts reversed or cyclically shifted click order.
    if (not cv2.isContourConvex(polygon) or cv2.contourArea(polygon, oriented=True) < .005
            or not (tl[0] < tr[0] and bl[0] < br[0] and tl[1] < bl[1] and tr[1] < br[1])):
        raise ValueError(CORNER_ERROR)


def visible_foot(box, height):
    """Bottom-center is a foot approximation only when the box bottom is visible."""
    x1, y1, x2, y2 = map(float, box)
    if not np.isfinite([x1, y1, x2, y2]).all() or x2 <= x1 or y2 <= y1 or y2 >= height - 1:
        return None
    return ((x1 + x2) / 2, y2)
