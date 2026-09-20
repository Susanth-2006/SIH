import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState, Alert } from '../components/ui/Feedback'
import { StatusBadge, POTHOLE_STATUS_CONFIG, confidencePct, formatDate } from '../utils/helpers'
import Modal, { DetailRow } from '../components/ui/Modal'
import { Wrench, CheckCircle, XCircle } from 'lucide-react'

export default function RepairManagement() {
  const [potholes, setPotholes] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadPotholes()
  }, [])

  const loadPotholes = async () => {
    setLoading(true)
    try {
      const data = await api.apiGet('/api/potholes?limit=200')
      const relevant = data.filter((p) =>
        ['VERIFIED', 'WORK_STARTED', 'WORK_FINISHED', 'REPAIR_VERIFICATION_PENDING', 'FIXED', 'REPAIR_FAILED'].includes(p.status)
      )
      setPotholes(relevant)
    } catch (e) {
      console.error('Failed to load repairs', e)
    } finally {
      setLoading(false)
    }
  }

  const performAction = async (action, pothole) => {
    try {
      const endpoints = {
        start: `/api/potholes/${pothole.id}/start-work`,
        finish: `/api/potholes/${pothole.id}/finish-work`,
      }
      await api.apiPost(endpoints[action], { officer_id: 1, notes: '' })
      setMessage(`Work ${action}ed for ${pothole.pothole_id}`)
      loadPotholes()
      const updated = await api.apiGet(`/api/potholes/${pothole.id}`)
      if (selected?.id === pothole.id) setSelected(updated)
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setMessage(''), 5000)
  }

  const verifyRepair = async (action, pothole) => {
    try {
      await api.apiPost(`/api/potholes/${pothole.id}/repair-verify`, {
        action: action === 'verify' ? 'REPAIR_VERIFIED' : 'REPAIR_FAILED',
        officer_id: 1,
        notes: '',
      })
      setMessage(`Repair ${action === 'verify' ? 'verified — pothole marked FIXED' : 'failed — pothole still present'}`)
      loadPotholes()
      const updated = await api.apiGet(`/api/potholes/${pothole.id}`)
      if (selected?.id === pothole.id) setSelected(updated)
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setMessage(''), 5000)
  }

  return (
    <div>
      {message && <Alert type={message.startsWith('Error') ? 'error' : 'success'}>{message}</Alert>}

      {loading ? (
        <LoadingState label="Loading repair work..." />
      ) : potholes.length === 0 ? (
        <EmptyState icon="🛠️" title="No active repair work" description="Verified potholes will appear here for repair workflow." />
      ) : (
        <div className="table-container card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Location</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Detected</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {potholes.map((p) => (
                <tr key={p.id}>
                  <td style={{ fontWeight: 700 }}>{p.pothole_id}</td>
                  <td>
                    <div>{p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}</div>
                  </td>
                  <td style={{ fontWeight: 600 }}>{p.severity.toUpperCase()}</td>
                  <td>{confidencePct(p.confidence)}</td>
                  <td>
                    <StatusBadge status={p.status} config={POTHOLE_STATUS_CONFIG} />
                  </td>
                  <td className="text-muted" style={{ fontSize: 12 }}>{formatDate(p.created_at)}</td>
                  <td>
                    <div className="actions-cell">
                      <button className="btn btn-outline btn-sm" onClick={() => setSelected(p)}>View</button>
                      {p.status === 'VERIFIED' && (
                        <button className="btn btn-primary btn-sm" onClick={() => performAction('start', p)}>
                          <Wrench size={13} /> Start
                        </button>
                      )}
                      {p.status === 'WORK_STARTED' && (
                        <button className="btn btn-warning btn-sm" onClick={() => performAction('finish', p)}>
                          <Wrench size={13} /> Finish
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.pothole_id}
        footer={
          selected && (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {selected.status === 'VERIFIED' && (
                <button className="btn btn-primary" onClick={() => performAction('start', selected)}>
                  <Wrench size={14} /> Start Work
                </button>
              )}
              {selected.status === 'WORK_STARTED' && (
                <button className="btn btn-warning" onClick={() => performAction('finish', selected)}>
                  <Wrench size={14} /> Finish Work
                </button>
              )}
              {selected.status === 'WORK_FINISHED' && (
                <>
                  <button className="btn btn-success" onClick={() => verifyRepair('verify', selected)}>
                    <CheckCircle size={14} /> Verify Repair
                  </button>
                  <button className="btn btn-danger" onClick={() => verifyRepair('fail', selected)}>
                    <XCircle size={14} /> Repair Failed
                  </button>
                </>
              )}
              <button className="btn btn-outline" onClick={() => setSelected(null)}>Close</button>
            </div>
          )
        }
      >
        {selected && (
          <>
            <div className="detail-list">
              <DetailRow label="Pothole ID" value={selected.pothole_id} />
              <DetailRow label="Status" value={<StatusBadge status={selected.status} config={POTHOLE_STATUS_CONFIG} />} />
              <DetailRow label="Severity" value={selected.severity.toUpperCase()} />
              <DetailRow label="Confidence" value={confidencePct(selected.confidence)} />
              <DetailRow label="Coordinates" value={`${selected.latitude.toFixed(5)}, ${selected.longitude.toFixed(5)}`} />
              <DetailRow label="Detected At" value={formatDate(selected.created_at)} />
            </div>

            <div className="divider" />

            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Repair Workflow</div>
            <div className="tracking-route">
              {['VERIFIED', 'WORK_STARTED', 'WORK_FINISHED', 'REPAIR_VERIFICATION_PENDING', 'FIXED'].map((stage) => {
                const stageIdx = ['VERIFIED', 'WORK_STARTED', 'WORK_FINISHED', 'REPAIR_VERIFICATION_PENDING', 'FIXED'].indexOf(stage)
                const currentIdx = ['VERIFIED', 'WORK_STARTED', 'WORK_FINISHED', 'REPAIR_VERIFICATION_PENDING', 'FIXED'].indexOf(selected.status)
                const done = stageIdx <= currentIdx
                const cfg = POTHOLE_STATUS_CONFIG[stage]
                return (
                  <div
                    key={stage}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '6px 0',
                      fontSize: 12.5,
                      color: done ? cfg.color : '#94a3b8',
                      fontWeight: done ? 600 : 400,
                    }}
                  >
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        background: done ? cfg.color : 'transparent',
                        border: `2px solid ${done ? cfg.color : '#cbd5e1'}`,
                        flexShrink: 0,
                      }}
                    />
                    <span>{cfg.label}</span>
                    {currentIdx === stageIdx && <span style={{ marginLeft: 'auto', fontSize: 11 }}>- current</span>}
                  </div>
                )
              })}
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}