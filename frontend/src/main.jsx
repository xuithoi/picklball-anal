import React, { useEffect, useRef, useState, useId } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowRight,
  Upload,
  Play,
  Pause,
  ScanLine,
  Crosshair,
  Layers,
  Download,
  ShieldCheck,
  Timer,
  Trash2,
  Check,
  X,
  RotateCcw,
  Video,
  CircleHelp,
  Menu,
} from "lucide-react";
import "./style.css";

const API = "/api";
const fileUrl = (id, name) => `${API}/jobs/${id}/files/${name}`;
const duration = (seconds) =>
  `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const players = ["#d5ff70", "#a695ff", "#ff9c70", "#73d8ea"];

function CourtScene({ time = 24, layer = "tracking", compact = false }) {
  const uid = useId().replaceAll(":", "");
  const project = (u, v) => [
    260 - 190 * v + u * (390 + 300 * v),
    100 + v * 390,
  ];
  const line = (u, v, x, y) => [...project(u, v), ...project(x, y)];
  const positions = [
    [0.26, 0.26],
    [0.73, 0.22],
    [0.28, 0.77],
    [0.74, 0.72],
  ].map(([x, y], i) => [
    x + Math.sin(time / 8 + i * 2) * 0.045,
    y + Math.cos(time / 11 + i) * 0.04,
  ]);
  return (
    <svg
      className={`court-scene ${compact ? "compact" : ""}`}
      viewBox="0 0 820 590"
      role="img"
      aria-label={
        layer === "heatmap"
          ? "Mô phỏng heatmap di chuyển trên sân pickleball"
          : "Mô phỏng theo dõi bốn người chơi trên sân pickleball"
      }
    >
      <defs>
        <pattern
          id={`${uid}-grid`}
          width="38"
          height="38"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 38 0 L 0 0 0 38"
            fill="none"
            stroke="#59635c"
            strokeWidth=".55"
            opacity=".28"
          />
        </pattern>
        <radialGradient id={`${uid}-heat`}>
          <stop stopColor="#edff77" stopOpacity=".9" />
          <stop offset=".4" stopColor="#c1fc55" stopOpacity=".65" />
          <stop offset="1" stopColor="#90d63f" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${uid}-surface`} x2="0" y2="1">
          <stop stopColor="#273c35" />
          <stop offset="1" stopColor="#1d302b" />
        </linearGradient>
        <filter id={`${uid}-glow`}>
          <feGaussianBlur stdDeviation="4" />
        </filter>
      </defs>
      <rect width="820" height="590" fill={`url(#${uid}-grid)`} />
      <ellipse cx="422" cy="442" rx="335" ry="99" fill="#000" opacity=".35" />
      <polygon
        points="242,76 665,76 798,510 32,510"
        fill="#17211e"
        stroke="#52674e"
        strokeWidth="1"
      />
      <polygon
        points="260,100 650,100 760,490 70,490"
        fill={`url(#${uid}-surface)`}
        stroke="#a8ba95"
        strokeWidth="2"
      />
      <polygon
        points={[
          project(0, 0.34),
          project(1, 0.34),
          project(1, 0.66),
          project(0, 0.66),
        ]
          .map((p) => p.join(","))
          .join(" ")}
        fill="#718253"
        opacity=".24"
      />
      {[
        line(0, 0.34, 1, 0.34),
        line(0, 0.66, 1, 0.66),
        line(0.5, 0, 0.5, 0.34),
        line(0.5, 0.66, 0.5, 1),
      ].map(([x1, y1, x2, y2], i) => (
        <line
          key={i}
          {...{ x1, y1, x2, y2 }}
          stroke="#a8ba95"
          strokeWidth="2"
          opacity=".75"
        />
      ))}
      {layer === "heatmap" &&
        positions.map(([x, y], i) => {
          const [cx, cy] = project(x, y);
          return (
            <ellipse
              key={i}
              {...{ cx, cy }}
              rx="110"
              ry="60"
              fill={`url(#${uid}-heat)`}
            />
          );
        })}
      {positions.map(([u, v], i) => {
        const [x, y] = project(u, v);
        const color = players[i];
        return (
          <g key={i}>
            {layer !== "court" && (
              <>
                <path
                  d={`M ${x - 30} ${y + 18} Q ${x + 45} ${y - 3} ${x - 14} ${y - 35} T ${x} ${y}`}
                  stroke={color}
                  strokeWidth="2"
                  strokeDasharray="4 5"
                  fill="none"
                  opacity=".55"
                />
                <ellipse
                  cx={x}
                  cy={y + 3}
                  rx="21"
                  ry="8"
                  fill={color}
                  opacity=".15"
                />
              </>
            )}
            <ellipse
              cx={x + 5}
              cy={y + 4}
              rx="15"
              ry="5"
              fill="#050b08"
              opacity=".6"
            />
            <g strokeLinecap="round">
              <path
                d={`M${x - 1} ${y - 17}l-8 20m9-20 9 19`}
                stroke="#c4c9c1"
                strokeWidth="5"
              />
              <path d={`M${x} ${y - 36}v20`} stroke={color} strokeWidth="12" />
              <circle cx={x} cy={y - 47} r="7" fill="#d4bca4" />
              <path
                d={`M${x - 5} ${y - 31}l-12 12m23-12 13 10`}
                stroke="#d4bca4"
                strokeWidth="4"
              />
              <ellipse
                cx={x + 24}
                cy={y - 20}
                rx="5"
                ry="8"
                fill={color}
                stroke="#d6dfcb"
                strokeWidth="1.5"
                transform={`rotate(-35 ${x + 24} ${y - 20})`}
              />
            </g>
            {layer === "tracking" && (
              <>
                <rect
                  x={x - 27}
                  y={y - 63}
                  width="55"
                  height="72"
                  rx="2"
                  fill={color}
                  fillOpacity=".04"
                  stroke={color}
                  strokeWidth="1.3"
                />
                <rect
                  x={x - 27}
                  y={y - 81}
                  width="55"
                  height="18"
                  rx="2"
                  fill={color}
                />
                <text
                  x={x}
                  y={y - 68}
                  textAnchor="middle"
                  fill="#142016"
                  fontFamily="monospace"
                  fontSize="11"
                  fontWeight="700"
                >
                  P{i + 1} · ID
                </text>
              </>
            )}
            {layer === "court" && (
              <>
                <circle cx={x} cy={y} r="17" fill={color} />
                <text
                  x={x}
                  y={y + 4}
                  textAnchor="middle"
                  fill="#142016"
                  fontSize="12"
                  fontWeight="800"
                >
                  P{i + 1}
                </text>
              </>
            )}
          </g>
        );
      })}
      <path
        d="M 170 298 L 712 298 L 712 281 L 170 281 Z"
        fill="#adbea2"
        opacity=".15"
      />
      <path
        d="M170 280H712M170 280v34m542-34v34"
        stroke="#ced8bc"
        strokeWidth="2"
      />
      <path d="M170 288H712M170 294H712" stroke="#b6c4ac" opacity=".4" />
      <text
        x="430"
        y="552"
        fill="#718474"
        textAnchor="middle"
        fontFamily="monospace"
        fontSize="10"
        letterSpacing="5"
      >
        P I C K L E B A L L / 2 0 × 4 4 F T
      </text>
      <g fill="#718474" fontFamily="monospace" fontSize="10">
        <text x="52" y="90">
          CAM 01 / COURT VIEW
        </text>
        <text x="664" y="555">
          SIMULATION
        </text>
      </g>
    </svg>
  );
}

function DemoPanel({ hero = false }) {
  const [playing, setPlaying] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [time, setTime] = useState(24);
  const [layer, setLayer] = useState("tracking");
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => setTime((t) => (t + 0.2) % 90), 200);
    return () => clearInterval(timer);
  }, [playing]);
  return (
    <div className={`demo-panel ${hero ? "hero-demo" : ""}`}>
      <div className="panel-top">
        <span>
          <span className="live-dot" /> COURT VISION{" "}
          <span className="muted">/ 01</span>
        </span>
        <span className="demo-tag">DEMO MÔ PHỎNG</span>
      </div>
      <div className="scene-wrap">
        <CourtScene time={time} layer={layer} />
        <div className="scene-label">
          <ScanLine size={14} />{" "}
          {layer === "tracking"
            ? "PLAYER TRACKING"
            : layer === "heatmap"
              ? "MOVEMENT HEATMAP"
              : "COURT POSITIONS"}
        </div>
        <div className="four-players">
          <strong>04</strong>
          <span>
            NGƯỜI CHƠI
            <br />
            TRONG MÔ PHỎNG
          </span>
        </div>
      </div>
      <div className="demo-controls">
        <button
          className="icon-button"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? "Tạm dừng demo" : "Phát demo"}
        >
          {playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <span className="mono time-label">{duration(time)}</span>
        <input
          aria-label="Tua demo"
          type="range"
          min="0"
          max="90"
          step=".2"
          value={time}
          onChange={(e) => setTime(Number(e.target.value))}
        />
        <span className="mono muted">01:30</span>
        <span className="demo-hd">DEMO</span>
      </div>
      <div className="layer-switch" aria-label="Chế độ xem demo">
        {[
          ["tracking", ScanLine, "Tracking"],
          ["heatmap", Layers, "Heatmap"],
          ["court", Crosshair, "Bản đồ sân"],
        ].map(([id, Icon, label]) => (
          <button
            key={id}
            className={layer === id ? "selected" : ""}
            onClick={() => setLayer(id)}
            aria-pressed={layer === id}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [corners, setCorners] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [dragging, setDragging] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const canvas = useRef(null);
  const busy =
    uploading ||
    (job && !["complete", "failed", "expired"].includes(job.state));
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!preview || job) return;
    const video = document.createElement("video");
    let disposed = false;
    video.preload = "auto";
    video.muted = true;
    video.src = preview;
    const draw = () => {
      if (disposed || !canvas.current) return;
      const c = canvas.current;
      c.width = video.videoWidth;
      c.height = video.videoHeight;
      c.getContext("2d").drawImage(video, 0, 0);
    };
    video.onloadeddata = () => {
      if (video.duration > 0.1)
        video.currentTime = Math.min(1, video.duration / 2);
      else draw();
    };
    video.onseeked = draw;
    video.onerror = () =>
      setError("Không thể xem trước video này. Hãy chọn MP4 mã hóa H.264.");
    return () => {
      disposed = true;
      video.onloadeddata = null;
      video.onseeked = null;
      video.onerror = null;
      video.removeAttribute("src");
      video.load();
    };
  }, [preview, job?.id]);
  useEffect(() => {
    if (!job?.id || ["complete", "failed", "expired"].includes(job.state))
      return;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const r = await fetch(`${API}/jobs/${job.id}`, {
          signal: controller.signal,
        });
        if (r.ok) {
          setJob(await r.json());
          setError("");
        } else if ([404, 410].includes(r.status)) {
          setJob((j) => ({ ...j, state: "expired" }));
        } else setError("Chưa lấy được trạng thái. Hệ thống sẽ thử lại.");
      } catch (e) {
        if (e.name !== "AbortError") setError("Mất kết nối. Đang thử lại…");
      }
    };
    const timer = setInterval(poll, 1500);
    return () => {
      clearInterval(timer);
      controller.abort();
    };
  }, [job?.id, job?.state]);
  function pick(selected) {
    if (!selected || busy) return;
    if (!selected.name.toLowerCase().endsWith(".mp4"))
      return setError("Vui lòng chọn một video MP4.");
    if (selected.size > 600 * 1024 * 1024)
      return setError("Video vượt quá giới hạn 600 MB.");
    setError("");
    setJob(null);
    setDeleted(false);
    setCorners([]);
    setFile(selected);
  }
  async function analyze() {
    if (!file || busy) return;
    setUploading(true);
    setError("");
    setDeleted(false);
    setJob(null);
    const form = new FormData();
    form.append("video", file);
    if (corners.length === 4) form.append("corners", JSON.stringify(corners));
    try {
      const r = await fetch(`${API}/jobs`, { method: "POST", body: form });
      const data = await r.json();
      if (!r.ok) throw Error(data.detail || "Không thể tải video lên.");
      setJob({
        id: data.id,
        state: "queued",
        progress: 0,
        calibrated: corners.length === 4,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }
  const remaining = job?.expires_at
    ? Math.max(0, Math.ceil(job.expires_at - now / 1000))
    : null;
  const expired = job?.state === "expired" || remaining === 0;
  const complete = job?.state === "complete" && !deleted && !expired;
  async function remove(confirmDownload = false) {
    if (
      !window.confirm(
        confirmDownload
          ? "Bạn đã lưu xong các tệp? Kết quả phân tích sẽ bị xóa vĩnh viễn."
          : "Xóa toàn bộ video và kết quả phân tích này?",
      )
    )
      return;
    try {
      const r = await fetch(
        `${API}/jobs/${job.id}${confirmDownload ? "/confirm-download" : ""}`,
        { method: confirmDownload ? "POST" : "DELETE" },
      );
      if (!r.ok) {
        const data = await r.json();
        throw Error(data.detail || "Không thể xóa tệp.");
      }
      setDeleted(true);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }
  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    setMobileNav(false);
  };
  return (
    <>
      <header className="site-header">
        <a className="brand" href="#" aria-label="Pickleball AI — trang chủ">
          <span className="brand-icon">
            <ScanLine size={23} />
          </span>
          <span>
            PICKLEBALL
            <span className="brand-ai">
              AI<span className="brand-period">.</span>
            </span>
          </span>
        </a>
        <nav className={mobileNav ? "open" : ""} aria-label="Điều hướng chính">
          <a href="#overview" onClick={() => setMobileNav(false)}>
            Tổng quan
          </a>
          <a href="#demo" onClick={() => setMobileNav(false)}>
            Trải nghiệm demo <span className="tiny-dot" />
          </a>
          <a href="#how-it-works" onClick={() => setMobileNav(false)}>
            Cách hoạt động
          </a>
        </nav>
        <button className="nav-cta" onClick={() => scrollTo("analyze")}>
          Vào sân phân tích <ArrowUpRight size={16} />
        </button>
        <button
          className="mobile-menu icon-button"
          onClick={() => setMobileNav((v) => !v)}
          aria-label="Mở menu"
          aria-expanded={mobileNav}
        >
          {mobileNav ? <X /> : <Menu />}
        </button>
      </header>
      <main>
        <section className="hero section-width" id="overview">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="live-dot" /> A NEW PERSPECTIVE ON YOUR GAME
            </div>
            <h1>
              THẤY RÕ
              <br />
              <span>CUỘC CHƠI.</span>
            </h1>
            <p className="hero-description">
              Mỗi bước di chuyển đều có câu chuyện.
              <br />
              Biến video trận đấu thành góc nhìn mới về cách bạn chơi
              pickleball.
            </p>
            <div className="hero-actions">
              <button className="primary" onClick={() => scrollTo("analyze")}>
                Phân tích video của bạn <ArrowUpRight size={19} />
              </button>
              <button className="text-button" onClick={() => scrollTo("demo")}>
                <span className="play-ring">
                  <Play size={12} fill="currentColor" />
                </span>{" "}
                Khám phá demo
              </button>
            </div>
            <div className="hero-note">
              <ShieldCheck size={15} /> Không cần camera trực tiếp <span /> Kết
              quả tự xóa sau 30 phút
            </div>
            <div className="hero-index">
              <span>01 — VIDEO IN.</span>
              <span>
                INSIGHTS OUT. <ArrowRight size={13} />
              </span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="visual-coordinate">
              VISION SYSTEM / MVP_01 <span>● OFFLINE ANALYSIS</span>
            </div>
            <DemoPanel hero />
            <div className="visual-caption">
              <span>
                <span className="lime-dash" /> THE COURT. DECODED.
              </span>
              <span>YOLO + BYTETRACK</span>
            </div>
          </div>
        </section>
        <div className="capability-strip">
          <div className="section-width">
            <span>
              <ScanLine />
              Theo dõi người chơi
            </span>
            <span>
              <Crosshair />
              Hiệu chỉnh sân
            </span>
            <span>
              <Layers />
              Heatmap di chuyển
            </span>
            <span>
              <Download />
              Xuất video & dữ liệu
            </span>
            <span>
              <Timer />
              Tự xóa kết quả
            </span>
          </div>
        </div>
        <section className="section-width demo-section" id="demo">
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                <span className="section-number">01 /</span> EXPLORE THE VISION
              </span>
              <h2>
                Đổi góc nhìn.
                <br />
                <span>Hiểu từng bước chân.</span>
              </h2>
            </div>
            <p>
              Chuyển giữa các lớp dữ liệu để khám phá kết quả.
              <br />
              Demo minh họa — không phải phân tích một trận đấu thật.
            </p>
          </div>
          <div className="demo-grid">
            <DemoPanel />
            <div className="demo-insights">
              <div className="insight-intro">
                <span className="outline-tag">YOUR POST-MATCH TOOLKIT</span>
                <h3>
                  Cả trận đấu.
                  <br /> Trong tầm mắt.
                </h3>
              </div>
              {[
                [
                  ScanLine,
                  "01",
                  "Nhận diện & theo dõi",
                  "Theo dõi tối đa 4 người chơi, gắn nhãn P1–P4 trên video.",
                ],
                [
                  Layers,
                  "02",
                  "Nhìn thấy chuyển động",
                  "Hiệu chỉnh 4 góc sân để xem vị trí và heatmap di chuyển tổng hợp.",
                ],
                [
                  Download,
                  "03",
                  "Mang dữ liệu ra khỏi sân",
                  "Tải video có chú thích và dữ liệu vị trí JSON để xem lại.",
                ],
              ].map(([Icon, n, title, desc]) => (
                <div className="insight" key={n}>
                  <div className="insight-icon">
                    <Icon size={19} />
                  </div>
                  <div>
                    <small>/{n}</small>
                    <h4>{title}</h4>
                    <p>{desc}</p>
                  </div>
                </div>
              ))}
              <div className="scope-note">
                <CircleHelp size={15} />
                <span>
                  MVP phân tích video ngoại tuyến. Chưa theo dõi bóng, đo tốc độ
                  hoặc tự chấm điểm.
                </span>
              </div>
            </div>
          </div>
        </section>
        <section className="workflow section-width" id="how-it-works">
          <div className="workflow-label">
            <span className="eyebrow">02 / SIMPLE BY DESIGN</span>
            <h2>Từ video đến góc nhìn mới.</h2>
          </div>
          <div className="steps">
            {[
              [
                "01",
                "Tải video",
                "Chọn MP4, tối đa 600 MB. Bắt đầu với clip 30–60 giây.",
              ],
              [
                "02",
                "Đánh dấu sân",
                "Chọn 4 góc sân để tạo heatmap và bản đồ vị trí.",
              ],
              [
                "03",
                "Xem & tải xuống",
                "Xem kết quả, tải tệp và xóa khi đã lưu xong.",
              ],
            ].map(([n, title, desc]) => (
              <div className="step" key={n}>
                <span>{n}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="analyze-section" id="analyze">
          <div className="section-width">
            <div className="section-heading">
              <div>
                <span className="eyebrow">
                  <span className="section-number">03 /</span> YOUR TURN
                </span>
                <h2>
                  Đến lượt <span>bạn.</span>
                </h2>
              </div>
              <p>
                Một video. Một góc nhìn khác.
                <br />
                Tải trận đấu lên và để AI bắt đầu công việc.
              </p>
            </div>
            <div className="workspace">
              <div className="workspace-top">
                <span>
                  <span className="live-dot" /> ANALYSIS WORKSPACE
                </span>
                <span className="outline-tag">MP4 · MAX 600 MB</span>
              </div>
              <div className="upload-layout">
                <div
                  className={`dropzone ${dragging ? "dragging" : ""} ${busy ? "disabled" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (!busy) setDragging(true);
                  }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragging(false);
                    pick(e.dataTransfer.files?.[0]);
                  }}
                >
                  <label>
                    <span className="upload-icon">
                      <Upload size={25} />
                    </span>
                    <strong>
                      {file ? file.name : "Thả video của bạn vào đây"}
                    </strong>
                    <span>
                      {file
                        ? `${(file.size / 1048576).toFixed(1)} MB · MP4`
                        : "hoặc nhấn để chọn tệp từ thiết bị"}
                    </span>
                    <span className="file-hint">
                      MP4 (H.264) · Tối đa 600 MB
                    </span>
                    <input
                      type="file"
                      accept="video/mp4,.mp4"
                      disabled={Boolean(busy)}
                      onChange={(e) => {
                        pick(e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                  </label>
                </div>
                <div className="upload-settings">
                  <span className="eyebrow">READY WHEN YOU ARE</span>
                  <h3>
                    Mang trận đấu
                    <br />
                    vào phòng phân tích.
                  </h3>
                  <p>
                    Dùng góc quay cố định, thấy rõ cả sân và bốn người chơi.
                    Video ngắn giúp bạn thử nhanh hơn.
                  </p>
                  <button
                    className="primary"
                    disabled={!file || Boolean(busy)}
                    onClick={analyze}
                  >
                    {uploading
                      ? "Đang tải video…"
                      : busy
                        ? "Đang phân tích…"
                        : "Phân tích video"}
                    <ArrowUpRight size={18} />
                  </button>
                  <small>
                    <ShieldCheck size={13} /> Tự xóa 30 phút sau khi xử lý xong
                  </small>
                </div>
              </div>
              {file && !job && (
                <div className="calibration">
                  <div className="calibration-heading">
                    <div>
                      <h3>
                        <Crosshair size={18} /> Hiệu chỉnh sân{" "}
                        <span className="outline-tag">TÙY CHỌN</span>
                      </h3>
                      <p>
                        Chọn 4 góc ngoài của sân theo thứ tự: trên trái → trên
                        phải → dưới phải → dưới trái. Cần bước này để có bản đồ
                        sân và heatmap.
                      </p>
                    </div>
                    <button
                      className="secondary"
                      onClick={() => setCorners([])}
                    >
                      <RotateCcw size={14} /> Chọn lại
                    </button>
                  </div>
                  <div
                    className="calframe"
                    onClick={(e) => {
                      const r = e.currentTarget.getBoundingClientRect();
                      if (corners.length < 4)
                        setCorners([
                          ...corners,
                          [
                            (e.clientX - r.left) / r.width,
                            (e.clientY - r.top) / r.height,
                          ],
                        ]);
                    }}
                  >
                    <canvas ref={canvas} />
                    {corners.map(([x, y], i) => (
                      <span
                        className="corner-dot"
                        key={i}
                        style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
                      >
                        {i + 1}
                      </span>
                    ))}
                  </div>
                  <div className="calibration-count">
                    <span className={corners.length === 4 ? "lime" : ""}>
                      {corners.length === 4 ? (
                        <Check size={14} />
                      ) : (
                        <Crosshair size={14} />
                      )}{" "}
                      {corners.length}/4 góc đã chọn
                    </span>
                    <span>Bỏ qua để chỉ xuất video theo dõi người chơi.</span>
                  </div>
                </div>
              )}
              {error && (
                <div className="message error" role="alert">
                  <CircleHelp size={17} />
                  {error}
                  <button
                    className="icon-button"
                    onClick={() => setError("")}
                    aria-label="Đóng thông báo"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
              {job && !deleted && !expired && (
                <div
                  className={`job-status ${job.state === "failed" ? "failed" : ""}`}
                  role="status"
                >
                  <div>
                    <span className="eyebrow">
                      {job.state === "failed"
                        ? "ANALYSIS FAILED"
                        : complete
                          ? "ANALYSIS COMPLETE"
                          : "PROCESSING YOUR GAME"}
                    </span>
                    <h3>
                      {job.state === "failed"
                        ? "Chưa thể xử lý video"
                        : complete
                          ? "Góc nhìn mới đã sẵn sàng."
                          : "Đang đọc từng khung hình…"}
                    </h3>
                    <p>
                      {job.message ||
                        "Video đang chờ xử lý. Bạn có thể giữ trang này mở để xem kết quả."}
                    </p>
                  </div>
                  <div className="progress-area">
                    <strong>
                      {job.progress || 0}
                      <span>%</span>
                    </strong>
                    <div className="progress-track">
                      <div style={{ width: `${job.progress || 0}%` }} />
                    </div>
                  </div>
                </div>
              )}
              {job?.expires_at && !deleted && !expired && (
                <div className="retention">
                  <Timer size={20} />
                  <div>
                    <strong>
                      Kết quả tự xóa sau{" "}
                      <span className="mono">{duration(remaining)}</span>
                    </strong>
                    <p>
                      Hãy tải tệp trước khi hết hạn. Lượt tải đang chạy được
                      hoàn tất trước khi xóa.
                    </p>
                  </div>
                  <div className="retention-actions">
                    <button className="secondary" onClick={() => remove(true)}>
                      <Check size={14} /> Đã tải xong · Xóa
                    </button>
                    <button
                      className="icon-button danger"
                      aria-label="Xóa kết quả"
                      onClick={() => remove()}
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </div>
              )}
              {(deleted || expired) && (
                <div className="message">
                  <ShieldCheck size={20} />
                  <div>
                    <strong>
                      {deleted
                        ? "Đã xóa hoặc chờ lượt tải hoàn tất để xóa."
                        : "Kết quả đã hết hạn."}
                    </strong>
                    <p>Bạn có thể phân tích lại hoặc chọn một video mới.</p>
                  </div>
                </div>
              )}
              {complete && (
                <div className="results">
                  <div className="result-video">
                    <div className="result-title">
                      <h3>
                        <Video size={17} /> Video theo dõi người chơi
                      </h3>
                      <span className="outline-tag">P1 — P4</span>
                    </div>
                    <video controls src={fileUrl(job.id, "annotated.mp4")} />
                    <div className="export-actions">
                      <a
                        className="primary"
                        href={fileUrl(job.id, "annotated.mp4")}
                        download
                      >
                        <Download size={16} /> Tải video
                      </a>
                      <a
                        className="secondary"
                        href={fileUrl(job.id, "positions.json")}
                        download
                      >
                        <Download size={16} /> Dữ liệu JSON
                      </a>
                    </div>
                  </div>
                  <div className="result-maps">
                    {job.calibrated ? (
                      [
                        ["court.png", "Bản đồ sân", Crosshair],
                        ["heatmap.png", "Heatmap di chuyển", Layers],
                      ].map(([name, label, Icon]) => (
                        <div className="map-result" key={name}>
                          <h3>
                            <Icon size={16} />
                            {label}
                            <a
                              href={fileUrl(job.id, name)}
                              download
                              aria-label={`Tải ${label}`}
                            >
                              <Download size={15} />
                            </a>
                          </h3>
                          <img src={fileUrl(job.id, name)} alt={label} />
                          <p>
                            {name === "court.png"
                              ? "Vị trí được phát hiện gần nhất."
                              : "Vị trí di chuyển tổng hợp của người chơi."}
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="uncalibrated">
                        <Crosshair size={30} />
                        <h3>Thêm một góc nhìn về sân.</h3>
                        <p>
                          Chọn 4 góc sân trước khi phân tích để có bản đồ vị trí
                          và heatmap.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="analysis-footnote">
              <CircleHelp size={14} />
              <span>
                Thời gian xử lý phụ thuộc độ dài video và phần cứng. Nhận diện
                có thể bỏ sót hoặc đổi ID khi người chơi bị che khuất.
              </span>
            </div>
          </div>
        </section>
      </main>
      <footer className="site-footer section-width">
        <a className="brand" href="#">
          <span className="brand-icon">
            <ScanLine size={20} />
          </span>
          <span>
            PICKLEBALL
            <span className="brand-ai">
              AI<span className="brand-period">.</span>
            </span>
          </span>
        </a>
        <span>A NEW PERSPECTIVE ON YOUR GAME.</span>
        <span className="footer-version">
          BUILT FOR THE COURT <span> / MVP 0.1</span>
        </span>
      </footer>
    </>
  );
}
createRoot(document.getElementById("root")).render(<App />);
