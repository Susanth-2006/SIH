import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState, Alert } from '../components/ui/Feedback'
import { StatusBadge, CHALLAN_STATUS_CONFIG, confidencePct, formatDate, getViolationTypeConfig } from '../utils/helpers'
import Modal, { DetailRow } from '../components/ui/Modal'
import { FileText, CheckCircle, Download } from 'lucide-react'

export default function ChallansPage() {
  const [challans, setChallans] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ status: 'ALL' })
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadChallans()
  }, [filters.status])

  const loadChallans = async () => {
    setLoading(true)
    try {
      let url = '/api/challans?limit=200'
      if (filters.status !== 'ALL') url += `&challan_status=${filters.status}`
      const data = await api.apiGet(url)
      setChallans(data)
    } catch (e) {
      console.error('Failed to load challans', e)
    } finally {
      setLoading(false)
    }
  }

  const updateStatus = async (challan, newStatus) => {
    try {
      await api.apiPatch(`/api/challans/${challan.id}`, { challan_status: newStatus })
      setMessage(`Challan ${challan.challan_id} marked as ${newStatus}`)
      loadChallans()
      if (selected?.id === challan.id) {
        const updated = await api.apiGet(`/api/challans/${challan.id}`)
        setSelected(updated)
      }
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
    setTimeout(() => setMessage(''), 5000)
  }

  const downloadChallan = (challan) => {
    const content = [
      '==============================================',
      '            URBAN INTELLIGENCE PLATFORM',
      '           DEMO TRAFFIC CHALLAN NOTICE',
      '==============================================',
      '',
      `Challan ID:      ${challan.challan_id}`,
      `Violation ID:    TV-${String(challan.violation_id).padStart(3, '0')}`,
      `Vehicle Number:  ${challan.vehicle_number || 'UNKNOWN'}`,
      `Violation Type:  ${challan.violation_type.replace('_', ' ')}`,
      `Fine Amount:     Rs. ${challan.fine_amount}`,
      `Detection Time:  ${formatDate(challan.detection_timestamp)}`,
      `GPS Location:    ${challan.latitude?.toFixed(5)}, ${challan.longitude?.toFixed(5)}`,
      `AI Confidence:   ${confidencePct(challan.ai_confidence)}`,
      `Verification:    ${challan.verification_status}`,
      `Status:          ${challan.challan_status}`,
      `Created:         ${formatDate(challan.created_at)}`,
      '',
      '==============================================',
      '  This is a DEMO challan for demonstration.',
      '  Not a legal traffic fine.',
      '==============================================',
    ].join('\n')

    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${challan.challan_id}_challan.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="filters-bar">
        <div className="filter-group">
          <label>Challan Status</label>
          <select className="filter-select" value={filters.status} onChange={(e) => setFilters({ status: e.target.value })}>
            <option value="ALL">All Statuses</option>
            <option value="GENERATED">Generated</option>
            <option value="PAID">Paid</option>
            <option value="DISPUTED">Disputed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
        {message && <Alert type={message.startsWith('Error') ? 'error' : 'success'}>{message}</Alert>}
      </div>

      {loading ? (
        <LoadingState label="Loading challans..." />
      ) : challans.length === 0 ? (
        <EmptyState icon="📝" title="No challans generated" description="Challans are auto-generated for AI-verified violations or after officer verification." />
      ) : (
        <div className="table-container card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th>Challan ID</th>
                <th>Vehicle</th>
                <th>Violation</th>
                <th>Fine</th>
                <th>Verification</th>
                <th>Status</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {challans.map((c) => {
                const cfg = getViolationTypeConfig(c.violation_type)
                return (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 700 }}>{c.challan_id}</td>
                    <td>{c.vehicle_number || <span className="text-muted">Unknown</span>}</td>
                    <td>
                      <span style={{ color: cfg.color, fontWeight: 600 }}>{cfg.label}</span>
                    </td>
                    <td style={{ fontWeight: 700 }}>Rs. {c.fine_amount}</td>
                    <td>
                      <StatusBadge
                        status={c.verification_status}
                        config={{
                          AI_VERIFIED: { label: 'AI Verified', color: '#22c55e', bg: 'rgba(34,197,94,0.1)' },
                          PENDING_OFFICER: { label: 'Pending', color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
                          OFFICER_VERIFIED: { label: 'Officer Verified', color: '#3b82f6', bg: 'rgba(59,130,246,0.1)' },
                          REJECTED: { label: 'Rejected', color: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
                        }}
                      />
                    </td>
                    <td>
                      <StatusBadge status={c.challan_status} config={CHALLAN_STATUS_CONFIG} />
                    </td>
                    <td className="text-muted" style={{ fontSize: 12 }}>{formatDate(c.created_at)}</td>
                    <td>
                      <div className="actions-cell">
                        <button className="btn btn-outline btn-sm" onClick={() => setSelected(c)}>
                          View
                        </button>
                        <button className="btn btn-outline btn-sm" onClick={() => downloadChallan(c)}>
                          <Download size={14} />
                        </button>
                      </div>
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
        title={selected?.challan_id}
        footer={
          selected && (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {selected.challan_status === 'GENERATED' && (
                <button className="btn btn-success" onClick={() => updateStatus(selected, 'PAID')}>
                  <CheckCircle size={14} /> Mark as Paid
                </button>
              )}
              {selected.challan_status !== 'DISPUTED' && (
                <button className="btn btn-warning" onClick={() => updateStatus(selected, 'DISPUTED')}>
                  Mark Disputed
                </button>
              )}
              {selected.challan_status !== 'CANCELLED' && (
                <button className="btn btn-danger" onClick={() => updateStatus(selected, 'CANCELLED')}>
                  Cancel Challan
                </button>
              )}
              <button className="btn btn-outline" onClick={() => downloadChallan(selected)}>
                <Download size={14} /> Download
              </button>
              <button className="btn btn-outline" onClick={() => setSelected(null)}>Close</button>
            </div>
          )
        }
      >
        {selected && (
          <>
            <div
              style={{
                background: 'linear-gradient(135deg, #1e293b, #0f172a)',
                borderRadius: 10,
                padding: '20px 24px',
                color: 'white',
                marginBottom: 16,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 11, opacity: 0.7, textTransform: 'uppercase', letterSpacing: 0.06 }}>Urban Intelligence Platform</div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>Traffic Challan Notice — DEMO</div>
                </div>
                <FileText size={28} opacity={0.6} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 12.5 }}>
                <div>
                  <div style={{ opacity: 0.7 }}>Challan No.</div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{selected.challan_id}</div>
                </div>
                <div>
                  <div style={{ opacity: 0.7 }}>Fine Amount</div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>Rs. {selected.fine_amount}</div>
                </div>
                <div>
                  <div style={{ opacity: 0.7 }}>Vehicle No.</div>
                  <div style={{ fontWeight: 700 }}>{selected.vehicle_number || 'UNKNOWN'}</div>
                </div>
                <div>
                  <div style={{ opacity: 0.7 }}>Violation</div>
                  <div style={{ fontWeight: 700 }}>{getViolationTypeConfig(selected.violation_type).label}</div>
                </div>
              </div>
            </div>
            <div className="detail-list">
              <DetailRow label="Challan ID" value={selected.challan_id} />
              <DetailRow label="Vehicle Number" value={selected.vehicle_number || 'Unknown'} />
              <DetailRow
                label="Violation Type"
                value={<span style={{ color: getViolationTypeConfig(selected.violation_type).color, fontWeight: 600 }}>{getViolationTypeConfig(selected.violation_type).label}</span>}
              />
              <DetailRow label="Fine Amount" value={`Rs. ${selected.fine_amount}`} />
              <DetailRow label="Detection Time" value={formatDate(selected.detection_timestamp)} />
              <DetailRow label="GPS Location" value={selected.latitude && selected.longitude ? `${selected.latitude.toFixed(5)}, ${selected.longitude.toFixed(5)}` : 'Not captured'} />
              <DetailRow label="AI Confidence" value={confidencePct(selected.ai_confidence)} />
              <DetailRow label="Verification" value={selected.verification_status} />
              <DetailRow label="Status" value={selected.challan_status} />
              <DetailRow label="Created" value={formatDate(selected.created_at)} />
              <DetailRow label="Last Updated" value={formatDate(selected.updated_at)} />
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}