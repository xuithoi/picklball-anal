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
import { requestJson } from "./api.js";
import VideoFramePicker, { frameTime } from "./VideoFramePicker.jsx";

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
          : layer === "ball"
            ? "Mô phỏng đường bóng trên sân pickleball"
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
      {layer === "ball" && (
        <g>
          <path
            d="M 300 405 Q 390 160 520 190 T 590 340"
            fill="none"
            stroke="#fff04e"
            strokeWidth="3"
            strokeDasharray="6 4"
          />
          <circle
            cx={440 + Math.sin(time / 5) * 100}
            cy={230 + Math.cos(time / 5) * 70}
            r="7"
            fill="#e9ff66"
          />
          <text
            x="280"
            y="530"
            fontFamily="monospace"
            fontSize="11"
            fill="#fff04e"
          >
            BALL TRAJECTORY / SIMULATED
          </text>
        </g>
      )}
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
              : layer === "ball"
                ? "BALL TRAJECTORY / DEMO"
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
          ["ball", ScanLine, "Đường bóng"],
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

function Brand() {
  return (
    <a
      className="brand kun-brand"
      href="#"
      aria-label="Pickleball Kun AI — trang chủ"
    >
      <img src="/brand/kun-logo.png" alt="" />
      <span>
        PICKLEBALL
        <span className="brand-ai">
          KUN AI<span className="brand-period">.</span>
        </span>
      </span>
    </a>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [corners, setCorners] = useState([]);
  const [selectionMode, setSelectionMode] = useState("court");
  const [ballSeed, setBallSeed] = useState(null);
  const [playerSeeds, setPlayerSeeds] = useState([null, null, null, null]);
  const [options, setOptions] = useState({
    player_count: 4,
    confidence: 0.3,
    inference_stride: 2,
    player_marker: "ellipse",
    player_trails: true,
    minimap_overlay: false,
    court_lines: false,
    heatmap_overlay: false,
    ball_tracking: false,
    ball_radius: 6,
    ball_tolerance: 15,
  });
  const [playerNames, setPlayerNames] = useState(["", "", "", ""]);
  const [summary, setSummary] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [frameReady, setFrameReady] = useState(false);
  const [startTime, setStartTime] = useState(0);
  const setOption = (name, value) =>
    setOptions((o) => ({ ...o, [name]: value }));
  const [uploading, setUploading] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [dragging, setDragging] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const canvas = useRef(null);
  const needsCourt = options.heatmap_overlay || options.minimap_overlay || options.court_lines;
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
  function confirmFrame(image, info) {
    if (!canvas.current) return;
    const target = canvas.current;
    target.width = info.width;
    target.height = info.height;
    target.getContext("2d").drawImage(image, 0, 0);
    setMetadata({ width: info.width, height: info.height, duration: info.duration });
    setStartTime(info.time);
    setFrameReady(true);
    setCorners([]);
    setBallSeed(null);
    setPlayerSeeds([null, null, null, null]);
    setSelectionMode("court");
    setError("");
  }
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
          setJob(await requestJson(r, "Không lấy được trạng thái tác vụ.", (data) => typeof data.id === "string" && typeof data.state === "string"));
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
  useEffect(() => {
    if (job?.state !== "complete" || deleted) return;
    const controller = new AbortController();
    fetch(fileUrl(job.id, "summary.json"), { signal: controller.signal })
      .then(async (r) => {
        return requestJson(r, "Không tải được báo cáo kết quả.");
      })
      .then(setSummary)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [job?.id, job?.state, deleted]);
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
    setBallSeed(null);
    setPlayerSeeds([null, null, null, null]);
    setMetadata(null);
    setFrameReady(false);
    setStartTime(0);
    setSummary(null);
    setOption("heatmap_overlay", false);
    setOption("minimap_overlay", false);
    setOption("court_lines", false);
    setFile(selected);
  }
  async function analyze() {
    if (!file || busy) return;
    if (!frameReady) return setError("Chờ video tải xong rồi xác nhận khung hình bắt đầu.");
    if (options.ball_tracking && !ballSeed)
      return setError(
        "Hãy chọn tâm bóng ở khung hình đã chọn trước khi phân tích.",
      );
    if (corners.length > 0 && corners.length < 4)
      return setError(
        "Hãy chọn đủ 4 góc sân hoặc bấm Chọn lại để bỏ hiệu chỉnh.",
      );
    if (needsCourt && corners.length !== 4)
      return setError("Chọn đủ 4 góc sân để hiển thị minimap, vạch sân hoặc heatmap trong video.");
    const named = playerNames.slice(0, options.player_count).some((name) => name.trim());
    const seeds = playerSeeds.slice(0, options.player_count);
    if ((named || seeds.some(Boolean)) && seeds.some((point) => !point))
      return setError("Hãy chọn vị trí cho đủ người chơi trên khung hình đã chọn để gán tên đúng người.");
    setSummary(null);
    setUploading(true);
    setError("");
    setDeleted(false);
    setJob(null);
    const form = new FormData();
    form.append("video", file);
    form.append(
      "options",
      JSON.stringify({
        ...options,
        start_time_s: startTime,
        player_names: playerNames.slice(0, options.player_count),
        player_seeds: seeds.every(Boolean) ? seeds : null,
        ball_seed: options.ball_tracking ? ballSeed : null,
      }),
    );
    if (corners.length === 4) form.append("corners", JSON.stringify(corners));
    try {
      await requestJson(await fetch(`${API}/health`), "Không kết nối được máy chủ phân tích.", (data) => data.ok === true);
      const r = await fetch(`${API}/jobs`, { method: "POST", body: form });
      const data = await requestJson(r, "Không thể tải video lên.", (value) => typeof value.id === "string" && value.id.length > 0);
      setJob({
        id: data.id,
        state: "queued",
        progress: 0,
        calibrated: corners.length === 4,
        options: {
          ...options,
          start_time_s: startTime,
          player_names: playerNames
            .slice(0, options.player_count)
            .map((name, i) => name.trim() || `P${i + 1}`),
        },
      });
    } catch (e) {
      setError(e instanceof TypeError ? "Không kết nối được máy chủ phân tích. Vui lòng thử lại." : e.message);
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
        await requestJson(r, "Không thể xóa tệp.");
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
        <Brand />
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
                  "Theo dõi 2 hoặc 4 người chơi, gắn nhãn P1–P4 trên video.",
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
                  MVP phân tích video ngoại tuyến. Bám bóng theo màu ở chế độ
                  thử nghiệm. Chưa đo tốc độ hoặc tự chấm điểm.
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
              {file && (
                <details className="input-video" open>
                  <summary><Play size={14} /> Chọn khung hình bắt đầu phân tích</summary>
                  <VideoFramePicker src={preview} selectedTime={startTime}
                    disabled={Boolean(busy || job)} onConfirm={confirmFrame} onError={setError} />
                </details>
              )}
              <fieldset className="analysis-options" disabled={Boolean(busy)}>
                <legend>
                  Thiết lập phân tích{" "}
                  <span className="outline-tag">INPUT → OUTPUT</span>
                </legend>
                <div className="option-fields">
                  <label>
                    Số người chơi
                    <select
                      aria-label="Số người chơi"
                      value={options.player_count}
                      onChange={(e) =>
                        setOption("player_count", Number(e.target.value))
                      }
                    >
                      <option value={2}>Đánh đơn · 2 người</option>
                      <option value={4}>Đánh đôi · 4 người</option>
                    </select>
                  </label>
                  <label>
                    Tần suất nhận diện
                    <select
                      aria-label="Tần suất nhận diện"
                      value={options.inference_stride}
                      onChange={(e) =>
                        setOption("inference_stride", Number(e.target.value))
                      }
                    >
                      <option value={1}>Mỗi khung hình · Chi tiết</option>
                      <option value={2}>Mỗi 2 khung hình · Cân bằng</option>
                      <option value={4}>Mỗi 4 khung hình · Nhanh hơn</option>
                    </select>
                  </label>
                  <label>
                    Độ tin cậy người chơi{" "}
                    <output>{Math.round(options.confidence * 100)}%</output>
                    <input
                      aria-label="Độ tin cậy người chơi"
                      type="range"
                      min="0.1"
                      max="0.9"
                      step="0.05"
                      value={options.confidence}
                      onChange={(e) =>
                        setOption("confidence", Number(e.target.value))
                      }
                    />
                    <small>
                      Tăng để lọc nhận diện yếu; có thể bỏ sót người ở xa.
                    </small>
                  </label>
                </div>
                <div className="athlete-roster">
                  <div className="roster-heading">
                    <h4>Tên vận động viên</h4>
                    <span className="outline-tag">
                      {options.player_count} NGƯỜI CHƠI
                    </span>
                  </div>
                  <div className="athlete-inputs">
                    {playerNames
                      .slice(0, options.player_count)
                      .map((name, i) => (
                        <label key={i}>
                          <span
                            className="player-chip"
                            style={{ color: players[i] }}
                          >
                            P{i + 1}
                          </span>
                          <span className="sr-only">
                            Tên vận động viên P{i + 1}
                          </span>
                          <input
                            type="text"
                            aria-label={`Tên vận động viên P${i + 1}`}
                            maxLength={40}
                            value={name}
                            placeholder={`Nhập tên vận động viên ${i + 1}`}
                            onChange={(e) =>
                              setPlayerNames((current) =>
                                current.map((value, index) =>
                                  index === i ? e.target.value : value,
                                ),
                              )
                            }
                          />
                        </label>
                      ))}
                  </div>
                  <p>
                    Tự nhập tên, rồi chọn vị trí từng người trên khung hình đã chọn bên dưới.
                    Hệ thống không tự nhận diện tên hay lấy tên từ demo.
                    Để trống tên sẽ dùng P1–P{options.player_count}.
                    AI vẫn có thể nhầm ID khi người chơi bị che khuất; hãy kiểm tra nhãn trong kết quả.
                  </p>
                </div>
                <div className="output-options">
                  <label>
                    <input type="checkbox"
                      checked={options.player_marker === "ellipse"}
                      onChange={(e) => setOption("player_marker", e.target.checked ? "ellipse" : "box")}
                    />
                    <span>
                      <strong>Vòng màu dưới chân</strong>
                      <small>Giữ màu P1–P{options.player_count} và tên đã nhập. Bỏ chọn để dùng khung chữ nhật.</small>
                    </span>
                  </label>
                  {[
                    ["minimap_overlay", "Minimap trong video", "Cần 4 góc sân. Cập nhật vị trí chân người chơi ở góc trái video."],
                    ["court_lines", "Vạch sân trên video", "Cần 4 góc sân. Vẽ đường biên, vạch bếp và đường giữa theo phối cảnh."],
                  ].map(([key, title, hint]) => (
                    <label key={key}>
                      <input type="checkbox" checked={options[key]}
                        onChange={(e) => setOption(key, e.target.checked)} />
                      <span><strong>{title}</strong><small>{hint}</small></span>
                    </label>
                  ))}
                  <label>
                    <input
                      type="checkbox"
                      checked={options.player_trails}
                      onChange={(e) =>
                        setOption("player_trails", e.target.checked)
                      }
                    />
                    <span>
                      <strong>Vệt di chuyển người chơi</strong>
                      <small>
                        Vẽ đường đi P1–P{options.player_count} trực tiếp trong
                        video.
                      </small>
                    </span>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={options.heatmap_overlay}
                      onChange={(e) =>
                        setOption("heatmap_overlay", e.target.checked)
                      }
                    />
                    <span>
                      <strong>Heatmap trong video</strong>
                      <small>
                        Cần 4 góc sân. Hiển thị mật độ vị trí người chơi ở góc
                        video.
                      </small>
                    </span>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={options.ball_tracking}
                      onChange={(e) => {
                        setOption("ball_tracking", e.target.checked);
                        setSelectionMode(e.target.checked ? "ball" : "court");
                      }}
                    />
                    <span>
                      <strong>
                        Đường bóng{" "}
                        <span className="outline-tag">THỬ NGHIỆM</span>
                      </strong>
                      <small>
                        Chọn bóng vàng/xanh ở khung hình đã chọn. Bám theo màu, chưa
                        phải AI bóng chuyên dụng.
                      </small>
                    </span>
                  </label>
                </div>
                {options.ball_tracking && (
                  <div className="ball-settings">
                    <label>
                      Bán kính bóng (pixel gốc){" "}
                      <output>{options.ball_radius}px</output>
                      <input
                        aria-label="Bán kính bóng"
                        type="range"
                        min="2"
                        max="30"
                        value={options.ball_radius}
                        onChange={(e) =>
                          setOption("ball_radius", Number(e.target.value))
                        }
                      />
                    </label>
                    <label>
                      Dung sai màu <output>{options.ball_tolerance}</output>
                      <input
                        aria-label="Dung sai màu"
                        type="range"
                        min="5"
                        max="40"
                        value={options.ball_tolerance}
                        onChange={(e) =>
                          setOption("ball_tolerance", Number(e.target.value))
                        }
                      />
                    </label>
                    <p>
                      Chọn chính giữa bóng trên ảnh bên dưới và chỉnh vòng tròn
                      vừa với bóng. Màu sân/trang phục giống bóng, nhòe hoặc che
                      khuất có thể gây bám nhầm. Đường vẽ ngắt khi không thấy
                      bóng.
                    </p>
                  </div>
                )}
                {!file && (
                  <p className="input-reminder">
                    <Upload size={14} /> Tải video lên để chọn góc sân và vị trí
                    bóng. Các tùy chọn sẽ được gửi cùng video.
                  </p>
                )}
              </fieldset>
              {file && !job && (
                <div className="calibration">
                  <div className="calibration-heading">
                    <div>
                      <h3>
                        <Crosshair size={18} /> Chuẩn bị khung hình đã chọn{" "}
                        <span className="outline-tag">
                          {options.ball_tracking || needsCourt || playerNames.slice(0, options.player_count).some((name) => name.trim())
                            ? "CẦN CHỌN ĐẦU VÀO"
                            : "TÙY CHỌN"}
                        </span>
                      </h3>
                      <p>
                        Chọn 4 góc ngoài của sân theo thứ tự: trên trái → trên
                        phải → dưới phải → dưới trái. Cần bước này để có minimap,
                        vạch sân và heatmap.
                      </p>
                    </div>
                    <button
                      className="secondary"
                      onClick={() => {
                        setCorners([]);
                        setBallSeed(null);
                        setPlayerSeeds([null, null, null, null]);
                        setSelectionMode("court");
                      }}
                    >
                      <RotateCcw size={14} /> Chọn lại
                    </button>
                  </div>
                  <div className="selection-toolbar">
                    <button
                      type="button"
                      className={
                        selectionMode === "court"
                          ? "secondary active"
                          : "secondary"
                      }
                      onClick={() => setSelectionMode("court")}
                    >
                      <Crosshair size={14} /> Chọn 4 góc sân
                    </button>
                    {options.ball_tracking && (
                      <button
                        type="button"
                        className={
                          selectionMode === "ball"
                            ? "secondary active"
                            : "secondary"
                        }
                        onClick={() => setSelectionMode("ball")}
                      >
                        <ScanLine size={14} /> Chọn tâm bóng
                      </button>
                    )}
                    <span>
                      {metadata
                        ? `${metadata.width} × ${metadata.height} · ${duration(metadata.duration)} · Khung đã chọn ${frameTime(startTime)}`
                        : "Đang đọc video…"}
                    </span>
                  </div>
                  {options.ball_tracking && (
                    <p className="selection-hint">
                      {ballSeed
                        ? "Đã chọn tâm bóng. Nhấn Chọn tâm bóng để chọn lại."
                        : "Chưa chọn bóng — chuyển sang Chọn tâm bóng, rồi nhấn vào chính giữa bóng."}
                    </p>
                  )}
                  <div className="selection-toolbar" aria-label="Gán tên cho người chơi">
                    {playerNames.slice(0, options.player_count).map((name, i) => (
                      <button type="button" key={i}
                        className={selectionMode === `player-${i}` ? "secondary active" : "secondary"}
                        onClick={() => setSelectionMode(`player-${i}`)}>
                        {playerSeeds[i] ? "✓ " : ""}Chọn P{i + 1}{name.trim() ? ` · ${name.trim()}` : ""}
                      </button>
                    ))}
                  </div>
                  <p className="selection-hint">
                    Chọn nút P1–P{options.player_count}, rồi nhấn vào giữa thân người tương ứng trong ảnh. Chọn lại nút rồi nhấn vào ảnh để sửa vị trí.
                    Các số 1–4 đánh dấu góc sân, không phải vận động viên.
                  </p>
                  <div
                    className="calframe"
                    onClick={(e) => {
                      const r = e.currentTarget.getBoundingClientRect();
                      if (!frameReady || uploading) return;
                      const point = [
                        (e.clientX - r.left) / r.width,
                        (e.clientY - r.top) / r.height,
                      ];
                      if (selectionMode.startsWith("player-")) {
                        const index = Number(selectionMode.split("-")[1]);
                        if (index >= options.player_count) return;
                        setPlayerSeeds((current) => current.map((value, i) => i === index ? point : value));
                      } else if (selectionMode === "ball" && options.ball_tracking)
                        setBallSeed(point);
                      else if (corners.length < 4)
                        setCorners([...corners, point]);
                    }}
                  >
                    <canvas ref={canvas} />
                    {options.ball_tracking && ballSeed && metadata && (
                      <span
                        className="ball-seed"
                        style={{
                          left: `${ballSeed[0] * 100}%`,
                          top: `${ballSeed[1] * 100}%`,
                          width: `${((options.ball_radius * 2) / metadata.width) * 100}%`,
                        }}
                      >
                        <span>BÓNG</span>
                      </span>
                    )}
                    {playerSeeds.slice(0, options.player_count).map((point, i) => point && (
                      <span className="player-seed" key={`player-${i}`}
                        style={{ left: `${point[0] * 100}%`, top: `${point[1] * 100}%`, color: players[i] }}>
                        P{i + 1}{playerNames[i].trim() ? ` · ${playerNames[i].trim()}` : ""}
                      </span>
                    ))}
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
                    <span>Minimap, vạch sân và heatmap cần đủ 4 góc sân.</span>
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
                        <Video size={17} /> Video phân tích
                      </h3>
                      <span className="outline-tag">
                        P1 — P{job.options?.player_count || 4}
                      </span>
                    </div>
                    <video controls src={fileUrl(job.id, "annotated.mp4")} />
                    {job.options?.player_names && (
                      <div
                        className="athlete-legend"
                        aria-label="Tên vận động viên trong kết quả"
                      >
                        {job.options.player_names.map((name, i) => (
                          <span key={i}>
                            <b style={{ color: players[i] }}>P{i + 1}</b>
                            {name}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="output-manifest">
                      <span>
                        <Check size={13} /> Nhãn người chơi
                      </span>
                      {job.options?.player_trails && (
                        <span>
                          <Check size={13} /> Vệt di chuyển
                        </span>
                      )}
                      {job.options?.minimap_overlay && (
                        <span><Check size={13} /> Minimap trong video</span>
                      )}
                      {job.options?.court_lines && (
                        <span><Check size={13} /> Vạch sân</span>
                      )}
                      {job.options?.heatmap_overlay && (
                        <span>
                          <Check size={13} /> Heatmap trong video
                        </span>
                      )}
                      {job.options?.ball_tracking && (
                        <span>
                          <ScanLine size={13} /> Bóng · Thử nghiệm
                        </span>
                      )}
                    </div>
                    {summary && (
                      <div className="analysis-report">
                        <strong>
                          {summary.tracked_players} người chơi được gán ID ·{" "}
                          {summary.frames} khung hình
                        </strong>
                        <p>Bắt đầu từ {frameTime(summary.start_time_s || 0)} của video gốc. Các mốc trong kết quả tính từ 00:00 của đoạn đã chọn.</p>
                        {summary.ball_tracking?.enabled && (
                          <p>
                            Bóng được quan sát:{" "}
                            {summary.ball_tracking.detected_frames}/
                            {summary.ball_tracking.total_frames} khung hình (
                            {Math.round(summary.ball_tracking.coverage * 100)}
                            %). Đây là tỉ lệ có điểm bám màu, không phải độ
                            chính xác.
                          </p>
                        )}
                        {summary.warnings?.length > 0 && (
                          <p className="warning-text">
                            Bám bóng theo màu có thể bỏ sót hoặc nhận nhầm. Kiểm
                            tra video trước khi sử dụng dữ liệu.
                            {summary.ball_tracking?.detected_frames === 0
                              ? " Không tìm thấy bóng; hãy chọn lại tâm và bán kính."
                              : ""}
                          </p>
                        )}
                      </div>
                    )}
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
                      {job.options?.ball_tracking && (
                        <a
                          className="secondary"
                          href={fileUrl(job.id, "ball.json")}
                          download
                        >
                          <Download size={16} /> Dữ liệu bóng
                        </a>
                      )}
                      <a
                        className="secondary"
                        href={fileUrl(job.id, "summary.json")}
                        download
                      >
                        <Download size={16} /> Báo cáo JSON
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
        <Brand />
        <span>A NEW PERSPECTIVE ON YOUR GAME.</span>
        <span className="footer-version">
          BUILT FOR THE COURT <span> / MVP 0.1</span>
        </span>
      </footer>
    </>
  );
}
createRoot(document.getElementById("root")).render(<App />);
