import { useEffect, useState } from 'react'
import {
  Bus,
  AlertTriangle,
  TrafficCone,
  ShieldAlert,
  Wrench,
  FileText,
  MapPin,
  TrendingUp,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react'
import { apiGet } from '../services/api'
import StatCard from '../components/ui/StatCard'
import { LoadingState } from '../components/ui/Feedback'
import { StatusBadge, VERIFICATION_STATUS_CONFIG, POTHOLE_STATUS_CONFIG, confidencePct, formatTime, getViolationTypeConfig } from '../utils/helpers'

export default function Dashboard({ stats, onRefresh }) {
  const [recentPotholes, setRecentPotholes] = useState([])
  const [recentViolations, setRecentViolations] = useState([])
  const [recentNotifications, setRecentNotifications] = useState([])

  useEffect(() => {
    loadRecentData()
  }, [])

  const loadRecentData = async () => {
    try {
      const [potholes, violations, notifications] = await Promise.all([
        apiGet('/api/potholes?limit=5'),
        apiGet('/api/traffic/violations?limit=5'),
        apiGet('/api/notifications?limit=5'),
      ])
      setRecentPotholes(potholes)
      setRecentViolations(violations)
      setRecentNotifications(notifications)
    } catch (e) {
      console.error('Failed to load recent data', e)
    }
  }

  if (!stats) return <LoadingState label="Loading dashboard..." />

  const fleetCards = [
    {
      label: 'Fleet Active',
      value: stats.fleet_active,
      icon: <Bus size={22} />,
      variant: 'accent',
    },
    {
      label: 'Fleet Offline',
      value: stats.fleet_offline,
      icon: <Bus size={22} />,
      variant: 'danger',
    },
    {
      label: 'Vehicles Tracked',
      value: stats.vehicles_tracked,
      icon: <MapPin size={22} />,
      variant: 'cyan',
    },
    {
      label: 'Total Potholes',
      value: stats.potholes_total,
      icon: <AlertTriangle size={22} />,
      variant: 'warning',
    },
  ]

  const potholeProgress = [
    { label: 'Pending Verification', value: stats.potholes_pending, variant: 'warning' },
    { label: 'Verified', value: stats.potholes_verified, variant: 'success' },
    { label: 'Work Started', value: stats.potholes_work_started, variant: 'cyan' },
    { label: 'Work Finished', value: stats.potholes_work_finished, variant: 'purple' },
    { label: 'Fixed', value: stats.potholes_fixed, variant: 'success' },
    { label: 'Repair Failed', value: stats.potholes_repair_failed, variant: 'danger' },
  ]

  const trafficCards = [
    {
      label: 'Total Violations',
      value: stats.violations_total,
      icon: <TrafficCone size={22} />,
      variant: 'danger',
    },
    {
      label: 'AI Verified',
      value: stats.violations_ai_verified,
      icon: <CheckCircle size={22} />,
      variant: 'success',
    },
    {
      label: 'Pending Verification',
      value: stats.violations_pending,
      icon: <Clock size={22} />,
      variant: 'warning',
    },
    {
      label: 'Officer Verified',
      value: stats.violations_officer_verified,
      icon: <ShieldAlert size={22} />,
      variant: 'accent',
    },
  ]

  const challanCards = [
    {
      label: 'Challans Generated',
      value: stats.challans_generated,
      icon: <FileText size={22} />,
      variant: 'purple',
    },
    {
      label: 'Challans Paid',
      value: stats.challans_paid,
      icon: <TrendingUp size={22} />,
      variant: 'success',
    },
  ]

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Fleet Overview</h2>
          <div className="grid grid-4">
            {fleetCards.map((c) => (
              <StatCard key={c.label} {...c} />
            ))}
          </div>
        </div>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Challan Summary</h2>
          <div className="grid grid-2">
            {challanCards.map((c) => (
              <StatCard key={c.label} {...c} />
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Pothole Workflow</h2>
          <div className="grid grid-3">
            {potholeProgress.map((p) => (
              <StatCard
                key={p.label}
                label={p.label}
                value={p.value}
                icon={<Wrench size={22} />}
                variant={p.variant}
              />
            ))}
          </div>
        </div>
        <div>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Traffic Enforcement</h2>
          <div className="grid grid-2">
            {trafficCards.map((c) => (
              <StatCard key={c.label} {...c} />
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-3">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent Potholes</h3>
          </div>
          {recentPotholes.length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>
              <div className="empty-state-icon">🕳️</div>
              <div>No potholes detected</div>
            </div>
          ) : (
            <div className="detail-list">
              {recentPotholes.map((p) => (
                <div className="detail-row" key={p.id}>
                  <div className="detail-label">
                    <span className="font-bold">{p.pothole_id}</span>
                    <div className="text-muted" style={{ fontSize: 11 }}>
                      {formatTime(p.created_at)}
                    </div>
                  </div>
                  <div className="detail-value" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <StatusBadge status={p.status} config={POTHOLE_STATUS_CONFIG} />
                    </div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>
                      {p.latitude.toFixed(4)}, {p.longitude.toFixed(4)} • Confidence {confidencePct(p.confidence)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent Traffic Violations</h3>
          </div>
          {recentViolations.length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>
              <div className="empty-state-icon">🚨</div>
              <div>No violations detected</div>
            </div>
          ) : (
            <div className="detail-list">
              {recentViolations.map((v) => {
                const cfg = getViolationTypeConfig(v.violation_type)
                return (
                  <div className="detail-row" key={v.id}>
                    <div className="detail-label">
                      <span className="font-bold">{v.violation_id}</span>
                      <div className="text-muted" style={{ fontSize: 11 }}>
                        {formatTime(v.created_at)}
                      </div>
                    </div>
                    <div className="detail-value" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ color: cfg.color, fontWeight: 600 }}>{cfg.label}</span>
                        <StatusBadge status={v.verification_status} config={VERIFICATION_STATUS_CONFIG} />
                      </div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>
                        {v.vehicle_number || 'Unknown'} • {confidencePct(v.confidence)}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recent System Notifications</h3>
          </div>
          {recentNotifications.length === 0 ? (
            <div className="empty-state" style={{ padding: 20 }}>
              <div className="empty-state-icon">🔔</div>
              <div>No notifications</div>
            </div>
          ) : (
            <div className="detail-list">
              {recentNotifications.map((n) => (
                <div className="detail-row" key={n.id}>
                  <div className="detail-label" style={{ width: 90 }}>
                    <StatusBadge status={n.notification_type} config={NOTIFICATION_TYPE_CONFIG} />
                  </div>
                  <div className="detail-value" style={{ display: 'flex', flexDirection: 'column' }}>
                    <div style={{ fontWeight: 600, fontSize: 12.5 }}>{n.title}</div>
                    <div className="text-muted" style={{ fontSize: 11 }}>
                      {formatTime(n.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const NOTIFICATION_TYPE_CONFIG = {
  POTHOLE_DETECTED: { label: 'Pothole', color: '#f59e0b' },
  VIOLATION_AI_VERIFIED: { label: 'Violation', color: '#ef4444' },
  VIOLATION_VERIFICATION_NEEDED: { label: 'Verify', color: '#f59e0b' },
  CHALLAN_GENERATED: { label: 'Challan', color: '#8b5cf6' },
  default: { label: 'System', color: '#64748b' },
}