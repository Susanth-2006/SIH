import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { Alert } from '../components/ui/Feedback'
import Modal, { DetailRow } from '../components/ui/Modal'
import EvidenceViewer from '../components/ui/EvidenceViewer'
import {
  Play, Video, MapPin, CheckCircle2, AlertTriangle, Loader2, Film, Upload, TrafficCone, Wrench, FileText,
  Eye,
} from 'lucide-react'

const STATUS_MESSAGES = {
  submitted: 'Submitting video to analysis engine...',
  processing: 'Analyzing frames — running traffic and pothole detection...',
  completed: 'Analysis complete. Incidents created and stored.',
  ml_unavailable: 'ML service is not running. Start the ML service (port 8001) and try again.',
  error: 'Video processing failed. See error details below.',
}

export default function VideoAnalysisPage({ onRefresh }) {
  const [vehicles, setVehicles] = useState([])
  const [videos, setVideos] = useState([])
  const [selectedVideo, setSelectedVideo] = useState('')
  const [uploadMode, setUploadMode] = useState('sample')
  const [uploadedFile, setUploadedFile] = useState(null)
  const [selectedVehicle, setSelectedVehicle] = useState('')
  const [gps, setGps] = useState({ startLat: '17.3600', startLng: '78.4700', endLat: '17.4200', endLng: '78.5300' })
  const [frameInterval, setFrameInterval] = useState(10)
  const [minConfidence, setMinConfidence] = useState(0.1)
  const [jobId, setJobId] = useState('')
  const [status, setStatus] = useState('idle')
  const [statusData, setStatusData] = useState(null)
  const [message, setMessage] = useState('')
  const [recentJobs, setRecentJobs] = useState([])
  const [detail, setDetail] = useState(null)
  const pollRef = useRef(null)
  const jobIdRef = useRef('')

  useEffect(() => {
    loadVehicles()
    loadVideos()
    loadJobs()
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const loadVehicles = async () => {
    try {
      const data = await api.apiGet('/api/fleet/')
      setVehicles(data)
      const bus = data.find((v) => v.vehicle_type === 'bus') || data[0]
      if (bus) setSelectedVehicle(String(bus.id))
    } catch (e) {
      console.error('Failed to load vehicles', e)
    }
  }

  const loadVideos = async () => {
    try {
      const data = await api.apiGet('/api/video/sample-videos')
      setVideos(data.videos || [])
      if (data.videos && data.videos.length > 0) setSelectedVideo(data.videos[0].name)
    } catch (e) {
      console.error('Failed to load sample videos', e)
    }
  }

  const loadJobs = async () => {
    try {
      const data = await api.apiGet('/api/video/jobs')
      setRecentJobs(data.slice(0, 6))
    } catch (e) {
      console.error('Failed to load jobs', e)
    }
  }

  const startAnalysis = async () => {
    const hasSource = uploadMode === 'sample' ? !!selectedVideo : !!uploadedFile
    if (!hasSource) {
      setMessage(uploadMode === 'sample' ? 'Error: Select a bus video first' : 'Error: Choose a video file to upload')
      return
    }
    setMessage('')
    setStatusData(null)
    setStatus('submitted')
    const formData = new FormData()
    if (uploadMode === 'sample') {
      formData.append('sample_filename', selectedVideo)
    } else {
      formData.append('file', uploadedFile)
    }
    if (selectedVehicle) formData.append('vehicle_id', selectedVehicle)
    formData.append('gps_start_lat', gps.startLat)
    formData.append('gps_start_lng', gps.startLng)
    formData.append('gps_end_lat', gps.endLat)
    formData.append('gps_end_lng', gps.endLng)
    formData.append('frame_interval', String(frameInterval))
    formData.append('min_confidence', String(minConfidence))

    try {
      const result = await api.apiUpload('/api/video/process', formData)
      setJobId(result.job_id)
      jobIdRef.current = result.job_id
      if (result.status === 'ml_unavailable') {
        setStatus('ml_unavailable')
        setMessage('ML service reached but returned an error. Check that port 8001 is up.')
      }
    } catch (err) {
      setStatus('error')
      setMessage(`Error: ${err.message}`)
      return
    }
    startPolling()
  }

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => pollStatus(jobIdRef.current), 2000)
  }

  const pollStatus = async (jid) => {
    if (!jid) return
    try {
      const data = await api.apiGet(`/api/video/status/${jid}`)
      setStatusData(data)
      setStatus(data.status)
      if (data.completed || data.status === 'completed') {
        if (pollRef.current) clearInterval(pollRef.current)
        setStatus('completed')
        loadJobs()
        if (onRefresh) onRefresh()
      } else if (data.status === 'ml_unavailable' || data.status === 'error') {
        if (pollRef.current) clearInterval(pollRef.current)
      }
    } catch (err) {
      console.error('Status poll failed', err)
    }
  }

  const progress = statusData?.progress ?? 0
  const trafficEvents = (statusData?.detections || []).filter((d) => d.type === 'traffic')
  const potholeEvents = (statusData?.detections || []).filter((d) => d.type === 'pothole')

  const renderEvidence = (d) => (
    <td>
      {d.evidence_url ? (
        <button
          className="evidence-thumb-btn"
          onClick={() => setDetail(d)}
          title="View evidence"
          style={{ padding: 0, border: 'none', background: 'none', cursor: 'pointer' }}
        >
          <img src={d.evidence_url} alt="evidence" style={{ width: 96, height: 64, objectFit: 'cover', borderRadius: 6 }} />
        </button>
      ) : (
        <span className="text-muted">—</span>
      )}
    </td>
  )

  return (
    <div>
      {message && <Alert type={message.startsWith('Error') ? 'error' : 'info'}>{message}</Alert>}

      <div className="filters-bar" style={{ marginBottom: 20 }}>
        <div className="filter-group">
          <label>Analysis Mode</label>
          <div className="filter-select" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px' }}>
            <Video size={15} /> Full video → traffic + pothole detection
          </div>
        </div>
        <div className="text-muted" style={{ fontSize: 12, alignSelf: 'center' }}>
          One video runs both detectors. Duplicate detections are merged into events, evidence is saved, and the 80% confidence workflow auto-verifies / sends low-confidence cases to the Verification Center.
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        {/* Left: bus footage + config */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className="stat-icon accent"><Film size={18} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>1 — Select Bus Footage</div>
              <div className="text-muted" style={{ fontSize: 12 }}>Videos recorded by the city bus camera</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
            <button
              type="button"
              className={uploadMode === 'sample' ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}
              onClick={() => { setUploadMode('sample'); setMessage(''); setStatus('idle'); setStatusData(null) }}
            >
              <Film size={14} /> Sample video
            </button>
            <button
              type="button"
              className={uploadMode === 'upload' ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm'}
              onClick={() => { setUploadMode('upload'); setMessage(''); setStatus('idle'); setStatusData(null) }}
            >
              <Upload size={14} /> Upload video
            </button>
          </div>

          {uploadMode === 'sample' ? (
            <div className="filter-group" style={{ marginBottom: 12 }}>
              <label>Bus camera video</label>
              <select
                className="filter-select"
                style={{ width: '100%' }}
                value={selectedVideo}
                onChange={(e) => {
                  setSelectedVideo(e.target.value)
                  setStatus('idle')
                  setMessage('')
                  setStatusData(null)
                }}
              >
                {videos.length === 0 && <option value="">No sample videos available</option>}
                {videos.map((v) => (
                  <option key={v.name} value={v.name}>{v.name} ({v.size_mb} MB)</option>
                ))}
              </select>
            </div>
          ) : (
            <div className="filter-group" style={{ marginBottom: 12 }}>
              <label>Upload camera footage (MP4/MOV/AVI)</label>
              <input
                type="file"
                accept="video/mp4,video/x-mp4,video/quicktime,video/x-msvideo,video/*"
                onChange={(e) => {
                  const f = e.target.files && e.target.files[0]
                  setUploadedFile(f || null)
                  setStatus('idle')
                  setMessage('')
                  setStatusData(null)
                }}
                style={{ width: '100%' }}
              />
              {uploadedFile && (
                <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  {uploadedFile.name} ({(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB)
                </div>
              )}
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="filter-group">
                <label>Camera Bus (fleet vehicle)</label>
                <select className="filter-select" style={{ width: '100%' }} value={selectedVehicle} onChange={(e) => setSelectedVehicle(e.target.value)}>
                  <option value="">Not assigned</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.id}>{v.fleet_id} — {v.vehicle_number}{v.vehicle_type === 'bus' ? ' (bus)' : ''}</option>
                  ))}
                </select>
              </div>
              <div className="filter-group">
                <label>Frame Interval (sample every N)</label>
                <input className="filter-input" type="number" min="1" max="100" value={frameInterval} onChange={(e) => setFrameInterval(parseInt(e.target.value) || 10)} />
              </div>
              <div className="filter-group">
                <label>Min Confidence (events below ignored)</label>
                <input className="filter-input" type="number" step="0.05" min="0.05" max="0.9" value={minConfidence} onChange={(e) => setMinConfidence(parseFloat(e.target.value) || 0.1)} />
              </div>
              <div className="filter-group">
                <label style={{ fontWeight: 600 }}><MapPin size={13} style={{ verticalAlign: -2 }} /> Simulated GPS Route</label>
                <div className="text-muted" style={{ fontSize: 11, marginTop: 2 }}>Bus route start → end; the polyline appears on the map</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
              <input className="filter-input" placeholder="Start Lat" value={gps.startLat} onChange={(e) => setGps({ ...gps, startLat: e.target.value })} />
              <input className="filter-input" placeholder="Start Lng" value={gps.startLng} onChange={(e) => setGps({ ...gps, startLng: e.target.value })} />
              <input className="filter-input" placeholder="End Lat" value={gps.endLat} onChange={(e) => setGps({ ...gps, endLat: e.target.value })} />
              <input className="filter-input" placeholder="End Lng" value={gps.endLng} onChange={(e) => setGps({ ...gps, endLng: e.target.value })} />
            </div>
          </div>
        </div>

        {/* Right: run + progress */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className="stat-icon success"><Play size={18} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>2 — Start Analysis</div>
              <div className="text-muted" style={{ fontSize: 12 }}>Background job, progress updates live</div>
            </div>
          </div>

          <button className="btn btn-primary" style={{ width: '100%', marginBottom: 16 }} onClick={startAnalysis}
            disabled={(uploadMode === 'sample' && !selectedVideo) || (uploadMode === 'upload' && !uploadedFile) || status === 'submitted' || status === 'processing'}>
            {status === 'submitted' || status === 'processing' ? <Loader2 size={16} className="spin-svg" /> : <Play size={16} />}
            {status === 'submitted' || status === 'processing' ? 'Analyzing...' : 'Start Analysis'}
          </button>

          {(status === 'submitted' || status === 'processing') && (
            <div style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
                <span className="text-muted">{STATUS_MESSAGES[status] || status}</span>
                <span style={{ fontWeight: 700 }}>{progress.toFixed(1)}%</span>
              </div>
              <div style={{ height: 10, background: 'rgba(255,255,255,0.08)', borderRadius: 6, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${progress}%`, background: 'linear-gradient(90deg,#3b82f6,#34d399)', transition: 'width 0.6s' }} />
              </div>
              <div style={{ display: 'flex', gap: 18, marginTop: 10, fontSize: 12, color: 'var(--text-muted, #94a3b8)' }}>
                <span>{statusData?.frames_processed ?? 0} / {statusData?.total_frames ?? 0} frames</span>
                <span>{statusData?.duration ?? 0}s video</span>
              </div>
              <div style={{ display: 'flex', gap: 24, marginTop: 10 }}>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#f97316' }}>{statusData?.traffic_detections ?? 0}</div>
                  <div className="text-muted" style={{ fontSize: 11 }}>Traffic events</div>
                </div>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: '#8b5cf6' }}>{statusData?.pothole_detections ?? 0}</div>
                  <div className="text-muted" style={{ fontSize: 11 }}>Pothole events</div>
                </div>
              </div>
            </div>
          )}

          {status === 'ml_unavailable' && (
            <div className="alert alert-warning" style={{ marginTop: 8 }}>
              <AlertTriangle size={16} />
              <span>ML analysis service is not reachable. Start the ML service on port 8001, then click Start Analysis again.</span>
            </div>
          )}

          {status === 'completed' && (
            <div style={{ marginTop: 8 }}>
              <div className="alert alert-success">
                <CheckCircle2 size={16} />
                <span>Analysis completed. {trafficEvents.length} traffic violation(s) and {potholeEvents.length} pothole(s) created. Detections appear on the map, verification center, challans, and repair queue.</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8, marginTop: 12 }}>
                <Link to="/map" className="btn btn-outline" style={{ padding: '8px 4px', justifyContent: 'center' }}><MapPin size={15} /> Map</Link>
                <Link to="/verification" className="btn btn-outline" style={{ padding: '8px 4px', justifyContent: 'center' }}><TrafficCone size={15} /> Verify</Link>
                <Link to="/challans" className="btn btn-outline" style={{ padding: '8px 4px', justifyContent: 'center' }}><FileText size={15} /> Challans</Link>
                <Link to="/repairs" className="btn btn-outline" style={{ padding: '8px 4px', justifyContent: 'center' }}><Wrench size={15} /> Repair</Link>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="alert alert-error" style={{ marginTop: 8 }}>
              <AlertTriangle size={16} />
              <span>{statusData?.error || 'Video processing failed.'}</span>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {status === 'completed' && (
        <>
          {(trafficEvents.length > 0 || potholeEvents.length > 0) ? (
            <div className="grid grid-2" style={{ marginBottom: 24 }}>
              <div className="card">
                <h3 style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}><TrafficCone size={16} /> Detected Traffic Violations</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="table">
                    <thead>
                      <tr><th>ID</th><th>Type</th><th>Confidence</th><th>Status</th><th>Plate</th><th>Challan</th><th>Evidence</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {trafficEvents.map((d) => (
                        <tr key={d.ref}>
                          <td style={{ fontWeight: 600 }}>{d.ref}</td>
                          <td>{d.violation_type}</td>
                          <td>{Math.round(d.confidence * 100)}%</td>
                          <td><span className={`status-badge ${d.status === 'AI_VERIFIED' ? 'success' : 'warning'}`}>{d.status}</span></td>
                          <td>{d.vehicle_number || <span className="text-muted">UNKNOWN</span>}</td>
                          <td><span className={`status-badge ${d.challan_status === 'GENERATED' ? 'success' : 'info'}`}>{d.challan_status}</span></td>
                          {renderEvidence(d)}
                          <td>
                            <button className="btn btn-outline btn-sm" onClick={() => setDetail(d)}>
                              <Eye size={14} /> View Details
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card">
                <h3 style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}><Wrench size={16} /> Detected Potholes</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="table">
                    <thead>
                      <tr><th>ID</th><th>Severity</th><th>Confidence</th><th>Status</th><th>Evidence</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {potholeEvents.map((d) => (
                        <tr key={d.ref}>
                          <td style={{ fontWeight: 600 }}>{d.ref}</td>
                          <td>
                            <span className={`status-badge ${d.severity === 'high' ? 'danger' : d.severity === 'medium' ? 'warning' : 'info'}`}>
                              {d.severity}
                            </span>
                          </td>
                          <td>{Math.round(d.confidence * 100)}%</td>
                          <td><span className="status-badge success">{d.status}</span></td>
                          {renderEvidence(d)}
                          <td>
                            <button className="btn btn-outline btn-sm" onClick={() => setDetail(d)}>
                              <Eye size={14} /> View Details
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="text-muted" style={{ fontSize: 11, marginTop: 8 }}>
                  Severity is estimated from bounding-box area ratio (physical depth is not measured from video).
                </div>
              </div>
            </div>
          ) : (
            <div className="alert alert-info">
              <Film size={16} />
              <span>Analysis completed with 0 detections in this video. Try a video containing riders/vehicles or road damage, or lower the confidence threshold.</span>
            </div>
          )}
        </>
      )}

      {/* Recent jobs */}
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>Recent Analysis Jobs</h3>
        {recentJobs.length === 0 ? (
          <div className="text-muted">No video jobs yet.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr><th>Job</th><th>File</th><th>Status</th><th>Progress</th><th>Traffic</th><th>Potholes</th></tr>
              </thead>
              <tbody>
                {recentJobs.map((j) => (
                  <tr key={j.job_id}>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{j.job_id}</td>
                    <td>{j.filename}</td>
                    <td><span className={`status-badge ${j.status === 'completed' ? 'success' : 'warning'}`}>{j.status}</span></td>
                    <td>{j.progress?.toFixed ? `${j.progress.toFixed(1)}%` : `${j.progress}%`}</td>
                    <td>{j.traffic_detections}</td>
                    <td>{j.pothole_detections}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detection details modal */}
      <Modal
        open={!!detail}
        onClose={() => setDetail(null)}
        title={detail?.type === 'traffic' ? `Traffic Violation ${detail?.ref || ''}` : `Pothole ${detail?.ref || ''}`}
        footer={
          <button className="btn btn-outline" onClick={() => setDetail(null)}>Close</button>
        }
      >
        {detail && (
          <>
            <EvidenceViewer
              image={detail.evidence_url}
              video={detail.evidence_video}
              title={`Evidence for ${detail.ref}`}
            />
            <div className="detail-list">
              {detail.type === 'traffic' ? (
                <>
                  <DetailRow label="Violation ID" value={detail.ref} />
                  <DetailRow label="Type" value={detail.violation_type} />
                  <DetailRow label="Confidence" value={`${Math.round(detail.confidence * 100)}%`} />
                  <DetailRow label="Verification Status" value={detail.status} />
                  <DetailRow label="Challan Status" value={detail.challan_status} />
                  <DetailRow label="Vehicle Number" value={detail.vehicle_number || 'UNKNOWN'} />
                  <DetailRow label="Coordinates" value={`${Number(detail.latitude).toFixed(5)}, ${Number(detail.longitude).toFixed(5)}`} />
                </>
              ) : (
                <>
                  <DetailRow label="Pothole ID" value={detail.ref} />
                  <DetailRow label="Severity" value={detail.severity} />
                  <DetailRow label="Confidence" value={`${Math.round(detail.confidence * 100)}%`} />
                  <DetailRow label="Status" value={detail.status} />
                  <DetailRow label="Coordinates" value={`${Number(detail.latitude).toFixed(5)}, ${Number(detail.longitude).toFixed(5)}`} />
                </>
              )}
              <DetailRow label="Job" value={jobId} />
              <DetailRow label="GPS Route" value="Simulated (start → end interpolated by video time)" />
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}