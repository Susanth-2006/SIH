import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState, Alert } from '../components/ui/Feedback'
import {
  StatusBadge,
  VERIFICATION_STATUS_CONFIG,
  POTHOLE_STATUS_CONFIG,
  confidencePct,
  formatDate,
  getViolationTypeConfig,
  ConfidenceBar,
} from '../utils/helpers'
import Modal, { DetailRow } from '../components/ui/Modal'
import EvidenceViewer from '../components/ui/EvidenceViewer'
import { CheckCircle, XCircle, ShieldAlert, AlertTriangle, MapPin } from 'lucide-react'

export default function VerificationCenter() {
  const [tab, setTab] = useState('traffic')
  const [potholes, setPotholes] = useState([])
  const [violations, setViolations] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [selectedViolation, setSelectedViolation] = useState(null)

  useEffect(() => {
    loadData()
  }, [tab])

  const loadData = async () => {
    setLoading(true)
    try {
      if (tab === 'traffic') {
        const data = await api.apiGet('/api/traffic/violations?verification_status=PENDING_OFFICER')
        setViolations(data)
      } else {
        const data = await api.apiGet('/api/potholes?status=PENDING_VERIFICATION')
        setPotholes(data)
      }
    } catch (e) {
      console.error('Failed to load verification data', e)
    } finally {
      setLoading(false)
    }
  }

  const handleTrafficVerify = async (violation, action) => {
    try {
      await api.apiPost(`/api/traffic/violations/${violation.id}/${action}`, { officer_id: 1, notes: '' })
      setMessage(action === 'verify' ? 'Violation verified. Challan generated.' : 'Violation rejected.')
      setSelectedViolation(null)
      loadData()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setMessage(''), 5000)
  }

  const handlePotholeVerify = async (pothole, action) => {
    try {
      await api.apiPost(`/api/potholes/${pothole.id}/verify`, { action: action.toUpperCase(), officer_id: 1, notes: '' })
      setMessage(`Pothole ${action.toLowerCase()}d.`)
      setSelected(null)
      loadData()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setMessage(''), 5000)
  }

  return (
    <div>
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(239,68,68,0.08))',
          border: '1px solid rgba(245,158,11,0.2)',
          borderRadius: 10,
          padding: '14px 18px',
          marginBottom: 20,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <ShieldAlert size={20} color="#d97706" />
        <div style={{ fontSize: 13, color: '#92400e' }}>
          Items below have confidence below 80% and require <strong>officer verification</strong> before workflow proceeds.
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === 'traffic' ? 'active' : ''}`} onClick={() => setTab('traffic')}>
          Traffic Violations
        </button>
        <button className={`tab ${tab === 'potholes' ? 'active' : ''}`} onClick={() => setTab('potholes')}>
          Potholes
        </button>
      </div>

      {message && <Alert type={message.startsWith('Error') ? 'error' : 'success'}>{message}</Alert>}

      {loading ? (
        <LoadingState label="Loading verification queue..." />
      ) : tab === 'traffic' ? (
        violations.length === 0 ? (
          <EmptyState icon="✅" title="No traffic violations awaiting verification" description="All traffic violations have been resolved." />
        ) : (
          <div className="grid grid-2">
            {violations.map((v) => (
              <div className="card" key={v.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div
                      style={{
                        width: 42,
                        height: 42,
                        borderRadius: 10,
                        background: 'rgba(239,68,68,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <AlertTriangle size={20} color="#ef4444" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700 }}>{v.violation_id}</div>
                      <div style={{ color: getViolationTypeConfig(v.violation_type).color, fontWeight: 600, fontSize: 13 }}>
                        {getViolationTypeConfig(v.violation_type).label}
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={v.verification_status} config={VERIFICATION_STATUS_CONFIG} />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Vehicle</span>
                    <span style={{ fontWeight: 600 }}>{v.vehicle_number || 'Unknown'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Confidence</span>
                    <ConfidenceBar confidence={v.confidence} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Location</span>
                    <span>
                      {v.latitude && v.longitude ? (
                        <span style={{ fontSize: 12 }}>
                          {v.latitude.toFixed(4)}, {v.longitude.toFixed(4)}
                        </span>
                      ) : (
                        'Not captured'
                      )}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-muted">Time</span>
                    <span>{formatDate(v.timestamp || v.created_at)}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                  <button className="btn btn-outline btn-sm" style={{ flex: 1 }} onClick={() => setSelectedViolation(v)}>
                    View Evidence
                  </button>
                  <button className="btn btn-success btn-sm" style={{ flex: 1 }} onClick={() => handleTrafficVerify(v, 'verify')}>
                    <CheckCircle size={14} /> Verify
                  </button>
                  <button className="btn btn-danger btn-sm" style={{ flex: 1 }} onClick={() => handleTrafficVerify(v, 'reject')}>
                    <XCircle size={14} /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )
      ) : potholes.length === 0 ? (
        <EmptyState icon="✅" title="No potholes awaiting verification" description="All potholes have been resolved." />
      ) : (
        <div className="grid grid-3">
          {potholes.map((p) => (
            <div className="card" key={p.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 42,
                      height: 42,
                      borderRadius: 10,
                      background: 'rgba(245,158,11,0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <AlertTriangle size={20} color="#f59e0b" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700 }}>{p.pothole_id}</div>
                    <div className="text-muted" style={{ fontSize: 12 }}>Pothole</div>
                  </div>
                </div>
                <StatusBadge status={p.status} config={POTHOLE_STATUS_CONFIG} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Confidence</span>
                  <ConfidenceBar confidence={p.confidence} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Location</span>
                  <span style={{ fontSize: 12 }}>
                    {p.latitude.toFixed(4)}, {p.longitude.toFixed(4)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Severity</span>
                  <span style={{ fontWeight: 600 }}>{p.severity.toUpperCase()}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="text-muted">Time</span>
                  <span>{formatDate(p.created_at)}</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                <button className="btn btn-outline btn-sm" style={{ flex: 1 }} onClick={() => setSelected(p)}>
                  View Evidence
                </button>
                <button className="btn btn-success btn-sm" style={{ flex: 1 }} onClick={() => handlePotholeVerify(p, 'verify')}>
                  <CheckCircle size={14} /> Verify
                </button>
                <button className="btn btn-danger btn-sm" style={{ flex: 1 }} onClick={() => handlePotholeVerify(p, 'reject')}>
                  <XCircle size={14} /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        open={!!selectedViolation}
        onClose={() => setSelectedViolation(null)}
        title={selectedViolation?.violation_id}
        footer={
          selectedViolation && (
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-success" onClick={() => handleTrafficVerify(selectedViolation, 'verify')}>
                <CheckCircle size={14} /> Verify Violation
              </button>
              <button className="btn btn-danger" onClick={() => handleTrafficVerify(selectedViolation, 'reject')}>
                <XCircle size={14} /> Reject Violation
              </button>
              <button className="btn btn-outline" onClick={() => setSelectedViolation(null)}>Close</button>
            </div>
          )
        }
      >
        {selectedViolation && (
          <>
            <EvidenceViewer
              image={selectedViolation.evidence_image}
              video={selectedViolation.evidence_video}
              title={`Evidence for ${selectedViolation.violation_id}`}
            />
            <div className="detail-list">
              <DetailRow label="Violation ID" value={selectedViolation.violation_id} />
              <DetailRow label="Type" value={getViolationTypeConfig(selectedViolation.violation_type).label} />
              <DetailRow label="Vehicle Number" value={selectedViolation.vehicle_number || 'Unknown'} />
              <DetailRow label="AI Confidence" value={confidencePct(selectedViolation.confidence)} />
              <DetailRow label="GPS Coordinates" value={selectedViolation.latitude && selectedViolation.longitude ? `${selectedViolation.latitude.toFixed(5)}, ${selectedViolation.longitude.toFixed(5)}` : 'Not captured'} />
              <DetailRow label="Timestamp" value={formatDate(selectedViolation.timestamp || selectedViolation.created_at)} />
              <DetailRow label="Detection Details" value={<pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{selectedViolation.detection_details || 'No additional details'}</pre>} />
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.pothole_id}
        footer={
          selected && (
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-success" onClick={() => handlePotholeVerify(selected, 'verify')}>
                <CheckCircle size={14} /> Verify Pothole
              </button>
              <button className="btn btn-danger" onClick={() => handlePotholeVerify(selected, 'reject')}>
                <XCircle size={14} /> Reject Pothole
              </button>
              <button className="btn btn-outline" onClick={() => setSelected(null)}>Close</button>
            </div>
          )
        }
      >
        {selected && (
          <>
            <EvidenceViewer
              image={selected.evidence_image}
              video={selected.evidence_video}
              title={`Evidence for ${selected.pothole_id}`}
            />
            <div className="detail-list">
              <DetailRow label="Pothole ID" value={selected.pothole_id} />
              <DetailRow label="Severity" value={selected.severity.toUpperCase()} />
              <DetailRow label="AI Confidence" value={confidencePct(selected.confidence)} />
              <DetailRow label="GPS Coordinates" value={`${selected.latitude.toFixed(5)}, ${selected.longitude.toFixed(5)}`} />
              <DetailRow label="Timestamp" value={formatDate(selected.created_at)} />
              {selected.detection_details && (
                <DetailRow label="Detection Details" value={<pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{selected.detection_details}</pre>} />
              )}
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}