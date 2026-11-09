import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { UploadCloud, Video, Activity, Download, Map, Layers, CheckCircle2 } from 'lucide-react';
import './style.css';
const API = '/api';
const fileUrl = (id, name) => `${API}/jobs/${id}/files/${name}`;
function App() {
  const [now, setNow] = useState(Date.now());
  const [deleted, setDeleted] = useState(false);
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [corners, setCorners] = useState([]);
  const [preview, setPreview] = useState('');
  const canvas = useRef(null);
  useEffect(() => { if (!file) return; const url = URL.createObjectURL(file); setPreview(url); return () => URL.revokeObjectURL(url); }, [file]);
  useEffect(() => { if (!file || !preview) return; const video = document.createElement('video'); video.preload = 'metadata'; video.src = preview; video.onloadeddata = () => { video.currentTime = Math.min(1, video.duration / 2); }; video.onseeked = () => { const c = canvas.current; if (!c) return; c.width = video.videoWidth; c.height = video.videoHeight; c.getContext('2d').drawImage(video, 0, 0); }; }, [file, preview]);
  useEffect(() => { if (!job?.id || ['complete', 'failed'].includes(job.state)) return; const timer = setInterval(async () => { try { const res = await fetch(`${API}/jobs/${job.id}`); if (res.ok) setJob(await res.json()); } catch {} }, 1500); return () => clearInterval(timer); }, [job?.id, job?.state]);
  function pick(e) { const selected = e.target.files?.[0]; if (!selected) return; setError(''); setJob(null); setDeleted(false); setCorners([]); if (!selected.name.toLowerCase().endsWith('.mp4')) return setError('Please choose an MP4 video.'); setFile(selected); }
  function clickCourt(e) { const r = e.currentTarget.getBoundingClientRect(); if (corners.length < 4) setCorners([...corners, [(e.clientX-r.left)/r.width, (e.clientY-r.top)/r.height]]); }
  async function analyze() { if (!file) return; setError(''); const form = new FormData(); form.append('video', file); if (corners.length === 4) form.append('corners', JSON.stringify(corners)); try { const res = await fetch(`${API}/jobs`, { method:'POST', body:form }); const data = await res.json(); if (!res.ok) throw Error(data.detail || 'Upload failed'); setJob({ id:data.id, state:'queued', progress:0 }); } catch(e) { setError(e.message); } }
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const remaining = job?.expires_at ? Math.max(0, Math.ceil(job.expires_at - now / 1000)) : null;
  const complete = job?.state === 'complete' && !deleted && (remaining === null || remaining > 0);
  const clock = remaining === null ? '' : `${String(Math.floor(remaining / 60)).padStart(2,'0')}:${String(remaining % 60).padStart(2,'0')}`;
  async function confirmDownloaded() {
    if (!job?.id || !window.confirm('Have you finished saving your files? This permanently deletes the analysis.')) return;
    try {
      const r = await fetch(`${API}/jobs/${job.id}/confirm-download`, {method:'POST'});
      if (!r.ok) throw new Error((await r.json()).detail || 'Deletion failed');
      setDeleted(true);
    } catch(e) {setError(e.message);}
  }
  async function deleteNow() {
    if (!job?.id || !window.confirm('Delete all analysis files now?')) return;
    try {
      const r = await fetch(`${API}/jobs/${job.id}`, {method:'DELETE'});
      if (!r.ok) throw new Error((await r.json()).detail || 'Deletion failed');
      setDeleted(true);
    } catch(e) {setError(e.message);}
  }
  return <div className="shell"><aside><div className="brand">◉ <span>Pickleball AI</span><small>MVP</small></div><div className="nav active"><Video size={19}/> Analyze Video</div><div className="nav"><Activity size={19}/> Offline analysis</div><div className="foot">YOLO + ByteTrack<br/>No live camera required</div></aside><main><header><h1>Analyze Match</h1><p>Upload an MP4, track players, and review court movement.</p></header><section className="upload card"><label className="drop"><UploadCloud size={32}/><strong>Upload Video</strong><span>Click to select an MP4 file</span><small>Recommended: 3–5 min • 1080p</small><input type="file" accept="video/mp4,.mp4" onChange={pick}/></label><div className="uploadinfo"><b>{file ? file.name : 'No video selected'}</b><span>{file ? `${(file.size/1048576).toFixed(1)} MB` : 'Select a file to begin'}</span></div><button onClick={analyze} disabled={!file || (job && !['failed','complete'].includes(job.state))}>Analyze Video</button></section>{file && !job && <section className="card calibration"><div><h3>Optional court calibration</h3><p>Click the four OUTER court corners in this order: top-left → top-right → bottom-right → bottom-left. Required for accurate court map and heatmap. If skipped, only player boxes are available.</p></div><div className="calframe" onClick={clickCourt}><canvas ref={canvas}/>{corners.map(([x,y],i) => <span key={i} className="dot" style={{left:`${x*100}%`,top:`${y*100}%`}}>{i+1}</span>)}</div><div className="calactions"><span>{corners.length}/4 corners selected</span><button className="secondary" onClick={() => setCorners([])}>Reset points</button></div></section>}{error && <p className="error">{error}</p>}{job && <section className="status card"><b>{job.state === 'failed' ? 'Processing failed' : complete ? 'Analysis complete' : 'Processing video...'}</b><span>{job.message}</span><div className="progress"><div style={{width:`${job.progress || 0}%`}}/></div><small>{job.progress || 0}%</small></section>}{job?.expires_at && !deleted && <section className="retention card"><div><strong>{remaining > 0 ? `Auto-delete in ${clock}` : 'Files expired'}</strong><p>Results are retained for 30 minutes after processing. Download your files before expiry.</p></div>{remaining > 0 && <div className="retention-buttons"><button className="secondary" onClick={confirmDownloaded}>I've downloaded — delete now</button><button className="secondary" onClick={deleteNow}>Delete files</button></div>}</section>}{deleted && <section className="card retention"><strong>Files deleted or scheduled for deletion after active downloads finish.</strong></section>}{complete && <div className="results"><section className="card player"><h3><Video size={19}/> Tracked Video</h3><video controls src={fileUrl(job.id,'annotated.mp4')}/><div className="actions"><a href={fileUrl(job.id,'annotated.mp4')} download><Download size={16}/> Export Video</a><a href={fileUrl(job.id,'positions.json')} download><Download size={16}/> Tracking Data</a></div></section><div className="side"><section className="card"><h3><Map size={19}/> Court Map</h3><img src={fileUrl(job.id,'court.png')} alt="Player positions on court"/><p>Latest positions. Requires calibration.</p></section><section className="card"><h3><Layers size={19}/> Movement Heatmap</h3><img src={fileUrl(job.id,'heatmap.png')} alt="Player movement heatmap"/><p>Aggregated tracked positions. Requires calibration.</p></section></div></div>}<footer><CheckCircle2 size={15}/> Offline video processing • No speed, ball tracking, or auto-scoring</footer></main></div>;
}
createRoot(document.getElementById('root')).render(<App/>);
