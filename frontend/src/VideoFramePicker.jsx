import React, { useEffect, useRef, useState } from "react";

export function frameTime(value) {
  const ms = Math.max(0, Math.floor((value || 0) * 1000));
  return `${String(Math.floor(ms / 60000)).padStart(2, "0")}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}.${String(ms % 1000).padStart(3, "0")}`;
}

export default function VideoFramePicker({ src, selectedTime, disabled, onConfirm, onError }) {
  const video = useRef(null);
  const snapshot = useRef(null);
  const callbacks = useRef({ onConfirm, onError });
  callbacks.current = { onConfirm, onError };
  const [ready, setReady] = useState(false);
  const [position, setPosition] = useState(0);
  const [length, setLength] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [precise, setPrecise] = useState(true);

  useEffect(() => {
    const media = video.current;
    if (!media || !src) return;
    let disposed = false;
    let handle;
    let initial = true;
    let latestPresentation = null;
    const canvas = document.createElement("canvas");
    const supported = typeof media.requestVideoFrameCallback === "function";
    setPrecise(supported);
    setReady(false);
    setPosition(0);
    setLength(0);
    setPlaying(false);
    snapshot.current = null;
    const capture = (time) => {
      if (disposed || media.readyState < 2 || !media.videoWidth) return;
      if (canvas.width !== media.videoWidth || canvas.height !== media.videoHeight) {
        canvas.width = media.videoWidth;
        canvas.height = media.videoHeight;
      }
      canvas.getContext("2d").drawImage(media, 0, 0);
      // Round down to FFmpeg's microsecond time base so it retains this frame.
      const info = {
        time: Math.floor(time * 1e6) / 1e6,
        width: canvas.width, height: canvas.height, duration: media.duration,
      };
      snapshot.current = { canvas, info };
      setReady(true);
      if (initial) {
        initial = false;
        callbacks.current.onConfirm(canvas, info);
      }
    };
    const settle = () => {
      if (disposed || media.seeking || media.readyState < 2 || !latestPresentation) return;
      const previous = snapshot.current;
      const currentPresentation = Math.abs(latestPresentation.position - media.currentTime) <= .000001 &&
        latestPresentation.time <= media.currentTime + 1e-9;
      if (currentPresentation && (!previous || latestPresentation.time !== previous.info.time)) {
        capture(latestPresentation.time);
        return;
      }
      if (!previous || previous.info.time > media.currentTime + 1e-9) return;
      // A seek within the same paused frame need not produce a new callback.
      // Keep its known timestamp only after verifying the decoded image matches.
      const probe = document.createElement("canvas");
      probe.width = canvas.width;
      probe.height = canvas.height;
      const context = probe.getContext("2d");
      context.drawImage(media, 0, 0);
      context.globalCompositeOperation = "difference";
      context.drawImage(previous.canvas, 0, 0);
      const pixels = context.getImageData(0, 0, probe.width, probe.height).data;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] || pixels[index + 1] || pixels[index + 2]) return;
      }
      setReady(true);
    };
    const tick = (_now, metadata) => {
      latestPresentation = { time: metadata.mediaTime, position: media.currentTime };
      settle();
      requestAnimationFrame(settle);
      if (!disposed) handle = media.requestVideoFrameCallback(tick);
    };
    const loaded = () => {
      if (Number.isFinite(media.duration)) setLength(media.duration);
      if (!supported && media.currentTime === 0) capture(0);
      else settle();
    };
    const seeking = () => setReady(false);
    const seeked = () => {
      if (!supported) {
        if (media.currentTime === 0) capture(0);
        else setReady(false);
        return;
      }
      settle();
      requestAnimationFrame(() => requestAnimationFrame(settle));
    };
    media.addEventListener("loadeddata", loaded);
    media.addEventListener("seeking", seeking);
    media.addEventListener("seeked", seeked);
    media.addEventListener("canplay", seeked);
    if (supported) handle = media.requestVideoFrameCallback(tick);
    if (media.readyState >= 2) loaded();
    return () => {
      disposed = true;
      media.pause();
      media.removeEventListener("loadeddata", loaded);
      media.removeEventListener("seeking", seeking);
      media.removeEventListener("seeked", seeked);
      media.removeEventListener("canplay", seeked);
      if (supported && handle !== undefined) media.cancelVideoFrameCallback(handle);
    };
  }, [src]);

  useEffect(() => { if (disabled) video.current?.pause(); }, [disabled]);

  function seek(value) {
    const media = video.current;
    if (!media || disabled) return;
    const target = Math.max(0, Math.min(value, Math.max(0, length - .001)));
    media.pause();
    if (Math.abs(media.currentTime - target) < .000001) return;
    setReady(false);
    media.currentTime = target;
    setPosition(target);
  }
  function confirm() {
    if (disabled || !ready || !snapshot.current) return;
    video.current.pause();
    const { canvas, info } = snapshot.current;
    callbacks.current.onConfirm(canvas, info);
  }

  return (
    <div className="frame-picker">
      <video ref={video} src={src} controls muted playsInline preload="auto"
        aria-label="Video đầu vào"
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
        onTimeUpdate={(event) => setPosition(event.currentTarget.currentTime)}
        onError={() => callbacks.current.onError("Không thể xem trước video này. Hãy chọn MP4 mã hóa H.264.")}
      />
      <label className="frame-timeline">
        <span>Tìm khung hình rõ bóng và đủ người chơi <output>{frameTime(position)} / {frameTime(length)}</output></span>
        <input type="range" aria-label="Thời điểm xem trước" min="0"
          max={Math.max(0, length - .001)} step="0.001" value={Math.min(position, Math.max(0, length - .001))}
          disabled={disabled || !length || !precise} onChange={(event) => seek(Number(event.target.value))} />
      </label>
      <div className="frame-picker-controls">
        <button type="button" className="secondary" disabled={disabled || !length}
          onClick={() => playing ? video.current.pause() : video.current.play().catch(() => callbacks.current.onError("Bấm nút phát trên video để xem trước."))}>
          {playing ? "Tạm dừng" : "Phát video"}
        </button>
        <button type="button" className="secondary" disabled={disabled || !length || !precise}
          onClick={() => seek(video.current.currentTime - 1 / 30)}>Lùi 1/30 giây</button>
        <button type="button" className="secondary" disabled={disabled || !length || !precise}
          onClick={() => seek(video.current.currentTime + 1 / 30)}>Tiến 1/30 giây</button>
        <button type="button" className="secondary active" disabled={disabled || !ready || (!precise && position > .000001)} onClick={confirm}>
          Dùng khung hình này
        </button>
      </div>
      <p role="status">Đã chọn bắt đầu tại <strong>{frameTime(selectedTime)}</strong>. Phân tích từ khung này đến hết video; kết quả bắt đầu ở 00:00.</p>
      <p>Đổi sang khung hình khác sẽ xóa các điểm sân, người và bóng; xác nhận lại cùng khung giữ các điểm đã chọn. Các nút tua dùng bước 1/30 giây; khung hình thực tế đang hiển thị được dùng khi xác nhận.</p>
      {!precise && <p role="alert">Trình duyệt này chỉ hỗ trợ chọn khung đầu. Dùng Chrome, Edge hoặc Safari bản mới để chọn khung hình khác.</p>}
    </div>
  );
}
