import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState } from '../components/ui/Feedback'
import { AlertTriangle, TrafficCone, FileText, Bell, Wrench } from 'lucide-react'

const TYPE_ICONS = {
  POTHOLE_DETECTED: { icon: AlertTriangle, label: 'Pothole', color: '#f59e0b' },
  POTHOLE_VERIFICATION_NEEDED: { icon: AlertTriangle, label: 'Pothole', color: '#f59e0b' },
  POTHOLE_VERIFIED: { icon: Wrench, label: 'Repair', color: '#10b981' },
  POTHOLE_REPAIR_FINISHED: { icon: Wrench, label: 'Repair', color: '#8b5cf6' },
  POTHOLE_REPAIR_VERIFIED: { icon: Wrench, label: 'Repair', color: '#22c55e' },
  VIOLATION_AI_VERIFIED: { icon: TrafficCone, label: 'Violation', color: '#ef4444' },
  VIOLATION_VERIFICATION_NEEDED: { icon: TrafficCone, label: 'Verify', color: '#f59e0b' },
  VIOLATION_OFFICER_VERIFIED: { icon: TrafficCone, label: 'Violation', color: '#3b82f6' },
  VIOLATION_REJECTED: { icon: TrafficCone, label: 'Rejected', color: '#ef4444' },
  CHALLAN_GENERATED: { icon: FileText, label: 'Challan', color: '#8b5cf6' },
}

export default function NotificationsPage({ onRefresh }) {
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    loadNotifications()
  }, [filter])

  const loadNotifications = async () => {
    setLoading(true)
    try {
      let url = '/api/notifications?limit=100'
      if (filter === 'UNREAD') url += '&is_read=false'
      const data = await api.apiGet(url)
      setNotifications(data)
    } catch (e) {
      console.error('Failed to load notifications', e)
    } finally {
      setLoading(false)
    }
  }

  const markRead = async (id) => {
    await api.apiPatch(`/api/notifications/${id}/read`)
    loadNotifications()
    if (onRefresh) onRefresh()
  }

  const markAllRead = async () => {
    await api.apiPatch('/api/notifications/read-all')
    loadNotifications()
    if (onRefresh) onRefresh()
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <div>
      <div className="filters-bar">
        <div className="filter-group">
          <label>Filter</label>
          <select className="filter-select" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="ALL">All Notifications</option>
            <option value="UNREAD">Unread Only</option>
          </select>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <button className="btn btn-outline" onClick={markAllRead}>
            Mark all read
          </button>
        </div>
      </div>

      <div style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
        {unreadCount > 0 ? `${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}` : 'All caught up'} • {notifications.length} total
      </div>

      {loading ? (
        <LoadingState label="Loading notifications..." />
      ) : notifications.length === 0 ? (
        <EmptyState icon="🔔" title="No notifications" description="Notifications appear when fleet detections occur." />
      ) : (
        <div>
          {notifications.map((n) => {
            const iconData = TYPE_ICONS[n.notification_type] || { icon: Bell, label: 'System', color: '#64748b' }
            const Icon = iconData.icon
            return (
              <div
                className={`notification-item ${n.is_read ? '' : 'unread'}`}
                key={n.id}
              >
                <div
                  className="notification-icon"
                  style={{ background: `${iconData.color}15`, color: iconData.color }}
                >
                  <Icon size={18} />
                </div>
                <div style={{ flex: 1 }}>
                  <div className="notification-title">{n.title}</div>
                  <div className="notification-message">{n.message}</div>
                  <div className="notification-time">
                    {new Date(n.created_at).toLocaleString('en-IN', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                  <span
                    className="status-badge"
                    style={{
                      color: iconData.color,
                      backgroundColor: `${iconData.color}10`,
                      borderColor: `${iconData.color}30`,
                      fontSize: 10.5,
                    }}
                  >
                    {iconData.label}
                  </span>
                  {!n.is_read && (
                    <button className="btn btn-outline btn-sm" onClick={() => markRead(n.id)}>
                      Mark read
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}