import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

# Canonical pickleball court (20 ft wide x 44 ft long), oriented vertically.
W, H = 400, 880
COLORS = [(244, 78, 125), (245, 181, 46), (34, 195, 168), (141, 97, 245)]  # RGB


def draw_court():
    canvas = np.full((H, W, 3), (162, 102, 46), dtype=np.uint8)  # BGR
    white = (245, 245, 245)
    cv2.rectangle(canvas, (4, 4), (W-5, H-5), white, 4)
    cv2.line(canvas, (0, H//2), (W, H//2), white, 4)  # net
    # Kitchen lines: 7 ft from net; court is 44 ft long.
    k = int(7 / 44 * H)
    cv2.line(canvas, (0, H//2-k), (W, H//2-k), white, 3)
    cv2.line(canvas, (0, H//2+k), (W, H//2+k), white, 3)
    cv2.line(canvas, (W//2, 0), (W//2, H//2-k), white, 3)
    cv2.line(canvas, (W//2, H//2+k), (W//2, H), white, 3)
    return canvas


def process_video(input_file: Path, out: Path, corners, progress):
    cap = cv2.VideoCapture(str(input_file))
    if not cap.isOpened():
        raise RuntimeError('Cannot read video; use H.264 MP4')
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width < 10 or height < 10:
        raise RuntimeError('Invalid video dimensions')
    # User must click four OUTER court corners in TL,TR,BR,BL order.
    transform = None
    if corners:
        source = np.float32([[x*width, y*height] for x, y in corners])
        target = np.float32([[0, 0], [W-1, 0], [W-1, H-1], [0, H-1]])
        transform = cv2.getPerspectiveTransform(source, target)
    model = YOLO(os.getenv('YOLO_MODEL', 'yolo11n.pt'))
    tmp = out / 'raw_annotated.mp4'
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError('Cannot initialize video writer')
    # Tracker IDs are not guaranteed to correspond to permanent identities.
    # Keep at most four player slots; prefer detections inside calibrated court.
    id_to_slot = {}
    trails = defaultdict(list)
    per_frame = []
    frame_idx = 0
    stride = max(1, int(os.getenv('INFERENCE_STRIDE', '2')))
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % stride == 0:
                result = model.track(frame, persist=True, tracker='bytetrack.yaml', classes=[0], conf=0.3, verbose=False)[0]
                observations = []
                if result.boxes is not None and result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    ids = result.boxes.id.int().cpu().tolist()
                    for box, track_id in zip(boxes, ids):
                        x1, y1, x2, y2 = map(float, box)
                        foot = np.array([[[ (x1+x2)/2, y2 ]]], dtype=np.float32)
                        point = None
                        if transform is not None:
                            xp, yp = cv2.perspectiveTransform(foot, transform)[0, 0]
                            if not (-25 <= xp <= W+25 and -25 <= yp <= H+25):
                                continue
                            point = [float(np.clip(xp, 0, W-1)), float(np.clip(yp, 0, H-1))]
                        if track_id not in id_to_slot:
                            if len(id_to_slot) >= 4:
                                continue
                            id_to_slot[track_id] = len(id_to_slot) + 1
                        slot = id_to_slot[track_id]
                        observations.append({'player': f'P{slot}', 'track_id': track_id, 'court_xy': point, 'box': [round(v, 1) for v in (x1,y1,x2,y2)]})
                        color = COLORS[slot-1]
                        bgr = (color[2], color[1], color[0])
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), bgr, 3)
                        cv2.putText(frame, f'P{slot}', (int(x1), max(20, int(y1)-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, bgr, 2)
                        if point:
                            trails[slot].append(point)
                per_frame.append({'time_s': round(frame_idx/fps, 2), 'players': observations})
            writer.write(frame)
            frame_idx += 1
            if frame_idx % 60 == 0:
                progress(min(94, int(94 * frame_idx / max(count, 1))), f'Processing frame {frame_idx} / {count or "?"}')
    finally:
        cap.release()
        writer.release()
    if frame_idx == 0:
        raise RuntimeError('Video contains no readable frames')
    progress(95, 'Preparing export')
    # Re-encode for browser compatibility if FFmpeg available; otherwise retain mp4v.
    final = out / 'annotated.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(tmp), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(final)]
    try:
        subprocess.run(cmd, check=True, timeout=1800)
        tmp.unlink(missing_ok=True)
    except (FileNotFoundError, subprocess.SubprocessError):
        tmp.rename(final)
    court = draw_court()
    heat = np.zeros((H, W), dtype=np.float32)
    for slot, points in trails.items():
        for x, y in points:
            cv2.circle(heat, (int(x), int(y)), 18, 1.0, -1)
        if points:
            x, y = points[-1]
            color = COLORS[slot-1]
            bgr = (color[2], color[1], color[0])
            cv2.circle(court, (int(x), int(y)), 11, bgr, -1)
            cv2.putText(court, f'P{slot}', (int(x)+13, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2)
    cv2.imwrite(str(out / 'court.png'), court)
    if heat.max() > 0:
        heat = cv2.GaussianBlur(heat, (0,0), 24)
        heat = (255 * heat / max(heat.max(), 0.0001)).astype(np.uint8)
        colored = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
        alpha = (heat.astype(np.float32) / 255 * 0.72)[:, :, None]
        blended = (court.astype(np.float32) * (1-alpha) + colored.astype(np.float32) * alpha).astype(np.uint8)
    else:
        blended = court.copy()
    cv2.imwrite(str(out / 'heatmap.png'), blended)
    (out / 'positions.json').write_text(json.dumps(per_frame))
    (out / 'summary.json').write_text(json.dumps({'duration_s': round(frame_idx/fps, 2), 'frames': frame_idx, 'tracked_players': len(trails), 'calibrated': transform is not None, 'note': 'Positions and heatmap are available only after court calibration. IDs may switch on occlusion.'}))
    progress(99, 'Finalizing')
