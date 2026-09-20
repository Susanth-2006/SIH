import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState } from '../components/ui/Feedback'
import {
  StatusBadge,
  VERIFICATION_STATUS_CONFIG,
  CHALLAN_STATUS_CONFIG,
  confidencePct,
  formatDate,
  formatTime,
  getViolationTypeConfig,
} from '../utils/helpers'
import Modal, { DetailRow } from '../components/ui/Modal'
import EvidenceViewer from '../components/ui/EvidenceViewer'

export default function TrafficViolationsPage() {
  const [violations, setViolations] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    type: 'ALL',
    verificationStatus: 'ALL',
    challanStatus: 'ALL',
    search: '',
  })
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    loadViolations()
  }, [filters.type, filters.verificationStatus, filters.challanStatus])

  const loadViolations = async () => {
    setLoading(true)
    try {
      let url = '/api/traffic/violations?limit=200'
      if (filters.type !== 'ALL') url += `&violation_type=${filters.type}`
      if (filters.verificationStatus !== 'ALL') url += `&verification_status=${filters.verificationStatus}`
      if (filters.challanStatus !== 'ALL') url += `&challan_status=${filters.challanStatus}`
      let data = await api.apiGet(url)
      if (filters.search) {
        data = data.filter(
          (v) =>
            (v.vehicle_number || '').toLowerCase().includes(filters.search.toLowerCase()) ||
            v.violation_id.toLowerCase().includes(filters.search.toLowerCase())
        )
      }
      setViolations(data)
    } catch (e) {
      console.error('Failed to load violations', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="filters-bar">
        <div className="filter-group">
          <label>Violation Type</label>
          <select className="filter-select" value={filters.type} onChange={(e) => setFilters({ ...filters, type: e.target.value })}>
            <option value="ALL">All Types</option>
            <option value="NO_HELMET">No Helmet</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Verification Status</label>
          <select className="filter-select" value={filters.verificationStatus} onChange={(e) => setFilters({ ...filters, verificationStatus: e.target.value })}>
            <option value="ALL">All Statuses</option>
            <option value="AI_VERIFIED">AI Verified</option>
            <option value="PENDING_OFFICER">Pending Officer</option>
            <option value="OFFICER_VERIFIED">Officer Verified</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Challan Status</label>
          <select className="filter-select" value={filters.challanStatus} onChange={(e) => setFilters({ ...filters, challanStatus: e.target.value })}>
            <option value="ALL">All Challan Statuses</option>
            <option value="NOT_GENERATED">Not Generated</option>
            <option value="GENERATED">Generated</option>
            <option value="PAID">Paid</option>
            <option value="DISPUTED">Disputed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Search</label>
          <input
            className="search-input"
            placeholder="Search vehicle / ID..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          />
        </div>
      </div>

      {loading ? (
        <LoadingState label="Loading traffic violations..." />
      ) : violations.length === 0 ? (
        <EmptyState icon="🚨" title="No violations found" description="Adjust filters or submit a detection via the API." />
      ) : (
        <div className="table-container card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Vehicle</th>
                <th>Confidence</th>
                <th>Verification</th>
                <th>Challan</th>
                <th>Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {violations.map((v) => {
                const cfg = getViolationTypeConfig(v.violation_type)
                return (
                  <tr key={v.id}>
                    <td style={{ fontWeight: 700 }}>{v.violation_id}</td>
                    <td>
                      <span style={{ color: cfg.color, fontWeight: 600 }}>{cfg.label}</span>
                    </td>
                    <td>{v.vehicle_number || <span className="text-muted">Unknown</span>}</td>
                    <td>
                      <div className="confidence-container">
                        <div className="confidence-bar">
                          <div
                            className="confidence-fill"
                            style={{
                              width: `${confidencePct(v.confidence).slice(0, -1)}%`,
                              backgroundColor: v.confidence >= 0.8 ? '#22c55e' : '#f59e0b',
                            }}
                          />
                        </div>
                        <span className="confidence-value" style={{ color: v.confidence >= 0.8 ? '#22c55e' : '#f59e0b' }}>
                          {confidencePct(v.confidence)}
                        </span>
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={v.verification_status} config={VERIFICATION_STATUS_CONFIG} />
                    </td>
                    <td>
                      <StatusBadge status={v.challan_status} config={CHALLAN_STATUS_CONFIG} />
                    </td>
                    <td className="text-muted" style={{ fontSize: 12 }}>
                      {formatDate(v.created_at)}
                    </td>
                    <td>
                      <button className="btn btn-outline btn-sm" onClick={() => setSelected(v)}>
                        View Details
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.violation_id}
        footer={
          <div style={{ display: 'flex', gap: 10 }}>
            {selected?.verification_status === 'PENDING_OFFICER' && (
              <>
                <button className="btn btn-success" onClick={() => handleVerify('verify', selected)}>
                  Verify Violation
                </button>
                <button className="btn btn-danger" onClick={() => handleVerify('reject', selected)}>
                  Reject Violation
                </button>
              </>
            )}
            <button className="btn btn-outline" onClick={() => setSelected(null)}>Close</button>
          </div>
        }
      >
        {selected && (
          <>
            <EvidenceViewer
              image={selected.evidence_image}
              video={selected.evidence_video}
              title={`Evidence for ${selected.violation_id}`}
            />
            <div className="detail-list">
              <DetailRow label="Violation ID" value={selected.violation_id} />
              <DetailRow
                label="Type"
                value={<span style={{ color: getViolationTypeConfig(selected.violation_type).color, fontWeight: 600 }}>{getViolationTypeConfig(selected.violation_type).label}</span>}
              />
              <DetailRow label="Vehicle Number" value={selected.vehicle_number || 'Unknown'} />
              <DetailRow label="Coordinates" value={selected.latitude && selected.longitude ? `${selected.latitude.toFixed(5)}, ${selected.longitude.toFixed(5)}` : 'Not captured'} />
              <DetailRow label="AI Confidence" value={confidencePct(selected.confidence)} />
              <DetailRow label="Detection Time" value={formatDate(selected.timestamp || selected.created_at)} />
              <DetailRow label="Verification Status" value={selected.verification_status} />
              <DetailRow label="Challan Status" value={selected.challan_status} />
              <DetailRow label="Fine Amount" value={selected.fine_amount ? `Rs. ${selected.fine_amount}` : 'Not generated'} />
              <DetailRow label="Detected By" value={selected.detected_by_vehicle_id ? `Vehicle #${selected.detected_by_vehicle_id}` : 'Unknown'} />
              {selected.detection_details && (
                <DetailRow label="Detection Details" value={<pre style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{selected.detection_details}</pre>} />
              )}
            </div>
          </>
        )}
      </Modal>
    </div>
  )

  async function handleVerify(action, violation) {
    try {
      const endpoint = action === 'verify' ? 'verify' : 'reject'
      await api.apiPost(`/api/traffic/violations/${violation.id}/${endpoint}`, { officer_id: 1, notes: '' })
      loadViolations()
      const updated = await api.apiGet(`/api/traffic/violations/${violation.id}`)
      setSelected(updated)
    } catch (e) {
      alert(`Error: ${e.message}`)
    }
  }
}