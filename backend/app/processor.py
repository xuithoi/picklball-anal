import json
import os
import subprocess
from collections import defaultdict, deque
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO
from .ball import ColorBallTracker
from .video import TimestampDecoder
from .options import AnalysisOptions
from .labels import draw_labels
from .overlays import W, H, COLORS, CourtOverlay, draw_player, draw_fading_trail


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


def heatmap_image(heat, court):
    """Density accumulates visits rather than overwriting previous observations."""
    if heat.max() <= 0:
        return court.copy()
    blurred = cv2.GaussianBlur(heat, (0, 0), 24)
    intensity = (255 * blurred / max(float(blurred.max()), .0001)).astype(np.uint8)
    colored = cv2.applyColorMap(intensity, cv2.COLORMAP_JET)
    alpha = (intensity.astype(np.float32) / 255 * .72)[:, :, None]
    return (court * (1 - alpha) + colored * alpha).astype(np.uint8)


def bind_player_seeds(boxes, ids, seeds, width, height):
    """Bind clicked athletes to distinct starting-frame tracker IDs, never detection order."""
    from scipy.optimize import linear_sum_assignment
    error = 'Không nhận diện đủ người tại vị trí đã chọn ở khung hình bắt đầu đã chọn. Chọn lại giữa thân từng người hoặc giảm độ tin cậy.'
    if len(boxes) < len(seeds) or len(set(ids)) != len(ids):
        raise ValueError(error)
    costs = np.full((len(seeds), len(boxes)), 1e6)
    for slot, (sx, sy) in enumerate(seeds):
        x, y = sx * width, sy * height
        for index, (x1, y1, x2, y2) in enumerate(boxes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                costs[slot, index] = ((x - (x1+x2)/2) / max(x2-x1, 1))**2 + ((y - (y1+y2)/2) / max(y2-y1, 1))**2
    rows, columns = linear_sum_assignment(costs)
    if len(rows) != len(seeds) or any(costs[r, c] >= 1e6 for r, c in zip(rows, columns)):
        raise ValueError(error)
    return {ids[c]: int(r) + 1 for r, c in zip(rows, columns)}


def process_video(input_file: Path, out: Path, corners, progress, options=None):
    settings = AnalysisOptions.model_validate(options or {})
    if (settings.heatmap_overlay or settings.minimap_overlay or settings.court_lines) and not corners:
        raise ValueError('Chọn đủ 4 góc sân để hiển thị minimap, vạch sân hoặc heatmap trong video.')
    cap = cv2.VideoCapture(str(input_file))
    writer = None
    decoder = None
    try:
        if not cap.isOpened():
            raise RuntimeError('Cannot read video; use H.264 MP4')
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or fps <= 0:
            fps = 30
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width < 10 or height < 10:
            raise RuntimeError('Invalid video dimensions')
        if count > 0 and settings.start_time_s >= count / fps:
            raise ValueError('Thời điểm bắt đầu phải nằm trước khi video kết thúc.')
        count = max(0, count - round(settings.start_time_s * fps))
        if settings.start_time_s > 0:
            decoder = TimestampDecoder(input_file, settings.start_time_s, width, height)
            cap.release()
        transform = None
        if corners:
            source = np.float32([[x * width, y * height] for x, y in corners])
            transform = cv2.getPerspectiveTransform(source, np.float32([[0, 0], [W-1, 0], [W-1, H-1], [0, H-1]]))
        overlay = CourtOverlay(width, height, corners)
        model = YOLO(os.getenv('YOLO_MODEL', 'yolo11n.pt'))
        tmp = out / 'raw_annotated.mp4'
        writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError('Cannot initialize video writer')
        id_to_slot = {}
        trails = defaultdict(list)
        image_trails = defaultdict(lambda: deque(maxlen=40))
        per_frame, ball_frames = [], []
        heat = np.zeros((H, W), dtype=np.float32)
        base_court = draw_court()
        mini_heat = base_court
        observations = []
        ball_tracker = None
        ball_detected = 0
        frame_idx = 0
        while True:
            ok, frame = decoder.read() if decoder is not None else cap.read()
            if not ok:
                break
            if settings.ball_tracking and ball_tracker is None:
                ball_tracker = ColorBallTracker(frame, settings.ball_seed, settings.ball_radius, settings.ball_tolerance, trail_length=max(4, min(90, round(fps * .7))))
            ball_point = ball_tracker.update(frame) if ball_tracker else None
            if ball_tracker:
                ball_detected += ball_point is not None
                ball_frames.append({'time_s': round(frame_idx / fps, 4), 'xy': list(map(int, ball_point)) if ball_point is not None else None})
            analyzed = frame_idx % settings.inference_stride == 0
            if analyzed:
                result = model.track(frame, persist=True, tracker='bytetrack.yaml', classes=[0], conf=settings.confidence, verbose=False)[0]
                observations = []
                if frame_idx == 0 and settings.player_seeds is not None:
                    boxes = result.boxes
                    if boxes is None or boxes.id is None:
                        raise ValueError('Không thấy người chơi ở khung hình bắt đầu đã chọn. Chọn video có đủ người hoặc giảm độ tin cậy.')
                    id_to_slot = bind_player_seeds(boxes.xyxy.cpu().numpy(), boxes.id.int().cpu().tolist(), settings.player_seeds, width, height)
                if result.boxes is not None and result.boxes.id is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    ids = result.boxes.id.int().cpu().tolist()
                    for box, track_id in zip(boxes, ids):
                        x1, y1, x2, y2 = map(float, box)
                        foot_xy = ((x1 + x2) / 2, y2)
                        point = None
                        if transform is not None:
                            xp, yp = cv2.perspectiveTransform(np.float32([[foot_xy]]), transform)[0, 0]
                            selected = settings.player_seeds is not None and track_id in id_to_slot
                            if not selected and not (-25 <= xp <= W+25 and -25 <= yp <= H+25):
                                continue
                            point = [float(xp), float(yp)]
                        if track_id not in id_to_slot:
                            if settings.player_seeds is not None:
                                continue
                            if len(id_to_slot) >= settings.player_count:
                                continue
                            id_to_slot[track_id] = len(id_to_slot) + 1
                        slot = id_to_slot[track_id]
                        observations.append({'player': f'P{slot}', 'name': settings.player_names[slot-1], 'track_id': track_id, 'court_xy': point, 'box': [round(float(v), 1) for v in box]})
                        history = image_trails[slot]
                        if history and frame_idx - history[-1][0] > settings.inference_stride:
                            history.clear()
                        history.append((frame_idx, tuple(map(int, foot_xy))))
                        if point is not None:
                            trails[slot].append(point)
                            if 0 <= point[0] < W and 0 <= point[1] < H:
                                visit = np.zeros_like(heat)
                                cv2.circle(visit, tuple(map(int, point)), 18, 1.0, -1)
                                heat += visit
                if settings.minimap_overlay:
                    overlay.update(observations)
                if settings.heatmap_overlay:
                    mini_heat = heatmap_image(heat, base_court)
            # Skipped frames retain the latest observations; JSON records inferred=False.
            if settings.court_lines:
                overlay.draw_lines(frame)
            name_labels = []
            for obs in observations:
                slot = int(obs['player'][1:])
                if settings.player_trails:
                    history = [point for _, point in image_trails[slot]]
                    draw_fading_trail(frame, history, COLORS[slot - 1][::-1])
                name_labels.append(draw_player(frame, obs, settings.player_marker))
            frame = draw_labels(frame, name_labels)
            if ball_tracker:
                ball_tracker.draw(frame, ball_point)
            if settings.minimap_overlay:
                overlay.draw_minimap(frame, settings.player_trails)
            if settings.heatmap_overlay:
                inset_h = min(int(height * .36), 240)
                inset_w = int(inset_h * W / H)
                if inset_h >= 40 and inset_w < width - 20:
                    inset = cv2.resize(mini_heat, (inset_w, inset_h))
                    top, left = height - inset_h - 8, width - inset_w - 8
                    frame[top:top+inset_h, left:left+inset_w] = inset
                    cv2.rectangle(frame, (left, top), (left+inset_w, top+inset_h), (112, 255, 213), 1)
                    cv2.putText(frame, 'HEATMAP', (left, max(12, top-5)), cv2.FONT_HERSHEY_SIMPLEX, .3, (112, 255, 213), 1)
            per_frame.append({'time_s': round(frame_idx/fps, 4), 'inferred': analyzed, 'players': observations})
            writer.write(frame)
            frame_idx += 1
            if frame_idx % 60 == 0:
                progress(min(94, int(94 * frame_idx / max(count, 1))), f'Processing frame {frame_idx} / {count or "?"}')
    finally:
        if decoder is not None:
            decoder.close()
        cap.release()
        if writer is not None:
            writer.release()
    if frame_idx == 0:
        raise RuntimeError('Video contains no readable frames')
    progress(95, 'Preparing export')
    final = out / 'annotated.mp4'
    try:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(tmp), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(final)], check=True, timeout=1800)
        tmp.unlink(missing_ok=True)
    except (FileNotFoundError, subprocess.SubprocessError):
        tmp.rename(final)
    court = base_court.copy()
    court_labels = []
    for slot, points in trails.items():
        if points and 0 <= points[-1][0] < W and 0 <= points[-1][1] < H:
            point = tuple(map(int, points[-1]))
            cv2.circle(court, point, 11, COLORS[slot-1][::-1], -1)
            name = settings.player_names[slot-1]
            court_labels.append((point[0]+13, point[1], f'P{slot} · {name}' if name != f'P{slot}' else name, COLORS[slot-1]))
    court = draw_labels(court, court_labels)
    cv2.imwrite(str(out / 'court.png'), court)
    cv2.imwrite(str(out / 'heatmap.png'), heatmap_image(heat, base_court))
    (out / 'positions.json').write_text(json.dumps(per_frame))
    (out / 'ball.json').write_text(json.dumps({'method': 'seeded_color_experimental' if ball_tracker else 'disabled', 'coordinates': 'video_pixels', 'frames': ball_frames}))
    warnings = []
    if ball_tracker:
        warnings.append('Experimental color tracking, not a trained pickleball detector. Similar colors, blur and occlusion may cause missing or incorrect observations; no trajectory is inferred through gaps.')
        if not ball_detected:
            warnings.append('No ball observations. Choose the visible ball center and radius on the selected starting frame, or disable ball tracking.')
    (out / 'summary.json').write_text(json.dumps({
        'start_time_s': settings.start_time_s, 'timeline': 'output_relative',
        'duration_s': round(frame_idx/fps, 2), 'frames': frame_idx, 'tracked_players': len(id_to_slot),
        'calibrated': transform is not None, 'options': settings.model_dump(),
        'players': [{'player': f'P{i+1}', 'name': name} for i, name in enumerate(settings.player_names)],
        'ball_tracking': {'enabled': bool(ball_tracker), 'detected_frames': ball_detected, 'total_frames': frame_idx, 'coverage': round(ball_detected/frame_idx, 4) if ball_tracker else None, 'seed_xy': list(ball_tracker.seed_xy) if ball_tracker else None, 'effective_radius': round(ball_tracker.radius, 2) if ball_tracker else None},
        'warnings': warnings,
        'note': 'Heatmap counts accumulated player detections, not ball movement. Court coordinates assume a planar court. Player IDs may switch on occlusion.',
    }))
    progress(99, 'Finalizing')
