export function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function confidencePct(conf) {
  if (conf === null || conf === undefined) return '—'
  return `${(conf * 100).toFixed(1)}%`
}

export const VIOLATION_TYPES = [
  { value: 'NO_HELMET', label: 'No Helmet', color: '#ef4444', icon: '🪖' },
  { value: 'OTHER', label: 'Other', color: '#64748b', icon: '⚠️' },
]

export function getViolationTypeConfig(type) {
  return VIOLATION_TYPES.find((t) => t.value === type) || VIOLATION_TYPES[VIOLATION_TYPES.length - 1]
}

export const POTHOLE_STATUS_CONFIG = {
  DETECTED: { label: 'Detected', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  PENDING_VERIFICATION: { label: 'Pending Verification', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  VERIFIED: { label: 'Verified', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  REJECTED: { label: 'Rejected', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  WORK_STARTED: { label: 'Work Started', color: '#06b6d4', bg: 'rgba(6,182,212,0.15)' },
  WORK_FINISHED: { label: 'Work Finished', color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  REPAIR_VERIFICATION_PENDING: { label: 'Repair Verification Pending', color: '#f97316', bg: 'rgba(249,115,22,0.15)' },
  FIXED: { label: 'Fixed', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
  REPAIR_FAILED: { label: 'Repair Failed', color: '#dc2626', bg: 'rgba(220,38,38,0.15)' },
}

export const VIOLATION_STATUS_CONFIG = {
  AI_DETECTED: { label: 'AI Detected', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  PENDING_VERIFICATION: { label: 'Pending Verification', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  VERIFIED: { label: 'Verified', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  REJECTED: { label: 'Rejected', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
}

export const VERIFICATION_STATUS_CONFIG = {
  AI_VERIFIED: { label: 'AI Verified', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
  PENDING_OFFICER: { label: 'Pending Officer', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  OFFICER_VERIFIED: { label: 'Officer Verified', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  REJECTED: { label: 'Rejected', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
}

export const CHALLAN_STATUS_CONFIG = {
  NOT_GENERATED: { label: 'Not Generated', color: '#94a3b8', bg: 'rgba(148,163,184,0.15)' },
  GENERATED: { label: 'Generated', color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  PAID: { label: 'Paid', color: '#22c55e', bg: 'rgba(34,197,94,0.15)' },
  DISPUTED: { label: 'Disputed', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  CANCELLED: { label: 'Cancelled', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
}

export function StatusBadge({ status, config }) {
  const cfg = config[status] || { label: status, color: '#94a3b8', bg: 'rgba(148,163,184,0.15)' }
  return (
    <span
      className="status-badge"
      style={{ color: cfg.color, backgroundColor: cfg.bg, borderColor: `${cfg.color}33` }}
    >
      {cfg.label}
    </span>
  )
}

export function ConfidenceBar({ confidence }) {
  const pct = confidence ? Math.round(confidence * 100) : 0
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <div className="confidence-container">
      <div className="confidence-bar">
        <div className="confidence-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="confidence-value" style={{ color }}>
        {pct}%
      </span>
    </div>
  )
}