import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState, Alert } from '../components/ui/Feedback'
import { StatusBadge, POTHOLE_STATUS_CONFIG, confidencePct, formatDate, formatTime } from '../utils/helpers'
import Modal, { DetailRow } from '../components/ui/Modal'
import EvidenceViewer from '../components/ui/EvidenceViewer'
import { AlertTriangle, Wrench, CheckCircle, Search } from 'lucide-react'

export default function PotholesPage() {
  const [potholes, setPotholes] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ status: 'ALL', severity: 'ALL' })
  const [selected, setSelected] = useState(null)
  const [actionMessage, setActionMessage] = useState('')

  useEffect(() => {
    loadPotholes()
  }, [filters])

  const loadPotholes = async () => {
    setLoading(true)
    try {
      let url = '/api/potholes?limit=200'
      if (filters.status !== 'ALL') url += `&status=${filters.status}`
      if (filters.severity !== 'ALL') url += `&severity=${filters.severity}`
      const data = await api.apiGet(url)
      setPotholes(data)
    } catch (e) {
      console.error('Failed to load potholes', e)
    } finally {
      setLoading(false)
    }
  }

  const handleWorkAction = async (action, potholeId) => {
    const notes = prompt(`Add notes for "${action}"?`)
    const endpoint = {
      START: `/api/potholes/${potholeId}/start-work`,
      FINISH: `/api/potholes/${potholeId}/finish-work`,
    }[action]
    try {
      await api.apiPost(endpoint, { notes: notes || '' })
      setActionMessage(`${action} action completed successfully`)
      loadPotholes()
      if (selected && selected.id === potholeId) {
        const updated = await api.apiGet(`/api/potholes/${potholeId}`)
        setSelected(updated)
      }
    } catch (e) {
      setActionMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setActionMessage(''), 5000)
  }

  const handleVerify = async (action) => {
    const notes = prompt(`Add notes for "${action}"?`)
    try {
      await api.apiPost(`/api/potholes/${selected.id}/verify`, {
        action,
        officer_id: 1,
        notes: notes || '',
      })
      setActionMessage(`Pothole ${action.toLowerCase()} successfully`)
      loadPotholes()
      const updated = await api.apiGet(`/api/potholes/${selected.id}`)
      setSelected(updated)
    } catch (e) {
      setActionMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setActionMessage(''), 5000)
  }

  const handleRepairVerify = async (action) => {
    const notes = prompt(`Add notes for "${action}"?`)
    try {
      await api.apiPost(`/api/potholes/${selected.id}/repair-verify`, {
        action,
        officer_id: 1,
        notes: notes || '',
      })
      setActionMessage(`Repair ${action.toLowerCase()} successfully`)
      loadPotholes()
      const updated = await api.apiGet(`/api/potholes/${selected.id}`)
      setSelected(updated)
    } catch (e) {
      setActionMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setActionMessage(''), 5000)
  }

  const renderSelectedFooter = () => {
    if (!selected) return null
    let buttons = []
    if (selected.status === 'PENDING_VERIFICATION') {
      buttons.push(
        <button key="v" className="btn btn-success" onClick={() => handleVerify('VERIFIED')}>
          <CheckCircle size={14} /> Verify
        </button>,
        <button key="r" className="btn btn-danger" onClick={() => handleVerify('REJECTED')}>
          Reject
        </button>
      )
    }
    if (selected.status === 'VERIFIED') {
      buttons.push(
        <button key="w" className="btn btn-primary" onClick={() => handleWorkAction('START', selected.id)}>
          <Wrench size={14} /> Start Work
        </button>
      )
    }
    if (selected.status === 'WORK_STARTED') {
      buttons.push(
        <button key="f" className="btn btn-warning" onClick={() => handleWorkAction('FINISH', selected.id)}>
          <Wrench size={14} /> Finish Work
        </button>
      )
    }
    if (selected.status === 'WORK_FINISHED') {
      buttons.push(
        <button key="rv" className="btn btn-success" onClick={() => handleRepairVerify('REPAIR_VERIFIED')}>
          <CheckCircle size={14} /> Verify Repair
        </button>,
        <button key="rf" className="btn btn-danger" onClick={() => handleRepairVerify('REPAIR_FAILED')}>
          Repair Failed
        </button>
      )
    }
    return buttons.length > 0 ? (
      <div style={{ display: 'flex', gap: 10 }}>{buttons}</div>
    ) : (
      <button className="btn btn-outline" onClick={() => setSelected(null)}>Close</button>
    )
  }

  return (
    <div>
      <div className="filters-bar">
        <div className="filter-group">
          <label>Status</label>
          <select className="filter-select" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="ALL">All Statuses</option>
            {Object.entries(POTHOLE_STATUS_CONFIG).map(([key, cfg]) => (
              <option key={key} value={key}>{cfg.label}</option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Severity</label>
          <select className="filter-select" value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
            <option value="ALL">All Severities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        {actionMessage && <Alert type={actionMessage.startsWith('Error') ? 'error' : 'success'}>{actionMessage}</Alert>}
      </div>

      {loading ? (
        <LoadingState label="Loading potholes..." />
      ) : potholes.length === 0 ? (
        <EmptyState icon="🕳️" title="No potholes found" description="Adjust filters or submit a detection via the API." />
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
                    <div className="text-muted" style={{ fontSize: 11 }}>{formatTime(p.created_at)}</div>
                  </td>
                  <td>
                    <span
                      className="status-badge"
                      style={{
                        color: p.severity === 'high' ? '#dc2626' : p.severity === 'medium' ? '#d97706' : '#16a34a',
                        backgroundColor: 'transparent',
                        borderColor: 'transparent',
                        fontWeight: 700,
                      }}
                    >
                      {p.severity.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    <div className="confidence-container">
                      <div className="confidence-bar">
                        <div
                          className="confidence-fill"
                          style={{
                            width: `${confidencePct(p.confidence).slice(0, -1)}%`,
                            backgroundColor: p.confidence >= 0.8 ? '#22c55e' : '#f59e0b',
                          }}
                        />
                      </div>
                      <span
                        className="confidence-value"
                        style={{ color: p.confidence >= 0.8 ? '#22c55e' : '#f59e0b' }}
                      >
                        {confidencePct(p.confidence)}
                      </span>
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={p.status} config={POTHOLE_STATUS_CONFIG} />
                  </td>
                  <td className="text-muted" style={{ fontSize: 12 }}>
                    {formatDate(p.created_at)}
                  </td>
                  <td>
                    <button className="btn btn-outline btn-sm" onClick={() => setSelected(p)}>
                      View Details
                    </button>
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
        title={selected ? selected.pothole_id : ''}
        footer={renderSelectedFooter()}
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
              <DetailRow label="Coordinates" value={`${selected.latitude.toFixed(5)}, ${selected.longitude.toFixed(5)}`} />
              <DetailRow label="Severity" value={selected.severity.toUpperCase()} />
              <DetailRow label="AI Confidence" value={confidencePct(selected.confidence)} />
              <DetailRow label="Status" value={selected.status} />
              <DetailRow label="Detected By" value={selected.detected_by_vehicle_id ? `Vehicle #${selected.detected_by_vehicle_id}` : 'Unknown'} />
              <DetailRow label="Detected At" value={formatDate(selected.created_at)} />
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