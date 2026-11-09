import React, { useEffect, useRef } from "react";

export default function BallSeedEditor({ image, seed, radius, frameKey, onChange, onRadiusChange }) {
  const canvas = useRef(null);
  const crop = useRef(null);
  useEffect(() => {
    if (!image || !seed || !canvas.current) return;
    const width = image.width, height = image.height;
    const x = Math.min(width - 1, Math.round(seed[0] * width));
    const y = Math.min(height - 1, Math.round(seed[1] * height));
    const size = Math.max(32, radius * 4);
    const cropWidth = Math.min(width, size), cropHeight = Math.min(height, size);
    const left = Math.max(0, Math.min(width - cropWidth, x - cropWidth / 2));
    const top = Math.max(0, Math.min(height - cropHeight, y - cropHeight / 2));
    crop.current = { left, top, width: cropWidth, height: cropHeight };
    const context = canvas.current.getContext("2d");
    context.imageSmoothingEnabled = false;
    context.clearRect(0, 0, 240, 240);
    context.drawImage(image, left, top, cropWidth, cropHeight, 0, 0, 240, 240);
    const cx = (x - left) / cropWidth * 240, cy = (y - top) / cropHeight * 240;
    context.strokeStyle = "#fff04e";
    context.lineWidth = 2;
    context.beginPath();
    context.ellipse(cx, cy, radius / cropWidth * 240, radius / cropHeight * 240, 0, 0, Math.PI * 2);
    context.stroke();
    context.strokeStyle = "#ffffff";
    context.beginPath();
    for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      context.moveTo(cx + dx * 4, cy + dy * 4);
      context.lineTo(cx + dx * 12, cy + dy * 12);
    }
    context.stroke();
  }, [image, seed, radius, frameKey]);

  if (!seed || !image) return <p className="selection-hint">Nhấn gần tâm bóng trên ảnh lớn để mở vùng phóng to và chỉnh chính xác.</p>;
  const x = Math.min(image.width - 1, Math.round(seed[0] * image.width));
  const y = Math.min(image.height - 1, Math.round(seed[1] * image.height));
  function select(px, py) {
    onChange([
      Math.max(0, Math.min(image.width - 1, Math.round(px))) / image.width,
      Math.max(0, Math.min(image.height - 1, Math.round(py))) / image.height,
    ]);
  }
  return (
    <div className="ball-seed-editor">
      <canvas ref={canvas} width="240" height="240" tabIndex="0" role="img"
        aria-label="Ảnh phóng to tâm bóng; dùng phím mũi tên để chỉnh từng pixel"
        onClick={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          const area = crop.current;
          if (!area) return;
          select(area.left + (event.clientX - bounds.left) / bounds.width * area.width,
                 area.top + (event.clientY - bounds.top) / bounds.height * area.height);
        }}
        onKeyDown={(event) => {
          const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
          if (delta) { event.preventDefault(); select(x + delta[0], y + delta[1]); }
        }}
      />
      <div>
        <h4>Phóng to và căn tâm bóng</h4>
        <p>Nhấn vào bóng trên ảnh phóng to, hoặc dịch tâm từng pixel bằng các nút mũi tên. Chỉnh bán kính để vòng tròn vừa với bóng.</p>
        <p className="mono" aria-live="polite">Tâm bóng: x={x}, y={y} · bán kính chọn {radius}px</p>
        <label className="seed-radius">
          Bán kính trên ảnh gốc: {radius}px
          <input type="range" aria-label="Bán kính bóng trong ảnh phóng to" min="2" max="30" step="1"
            value={radius} onChange={(event) => onRadiusChange(Number(event.target.value))} />
        </label>
        <div className="seed-nudges">
          {[["←", -1, 0, "trái"], ["→", 1, 0, "phải"], ["↑", 0, -1, "lên"], ["↓", 0, 1, "xuống"]].map(([label, dx, dy, name]) => (
            <button key={name} type="button" className="secondary" aria-label={`Dịch tâm bóng ${name} 1 pixel`}
              onClick={() => select(x + dx, y + dy)}>{label}</button>
          ))}
        </div>
        <p>Hệ thống sẽ tìm vùng bóng gần điểm chọn. Nếu bóng bị che hoặc nhìn trắng hoàn toàn, hãy chọn khung hình khác.</p>
      </div>
    </div>
  );
}
