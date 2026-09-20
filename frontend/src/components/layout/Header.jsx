import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, MapPin, AlertTriangle, TrafficCone, ShieldAlert, FileText, LogOut, ChevronDown } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../context/AuthContext'

const pageTitles = {
  '/': { title: 'Dashboard', subtitle: 'Urban Intelligence Platform Overview' },
  '/fleet': { title: 'Live Fleet', subtitle: 'Fleet Vehicles & GPS Tracking' },
  '/video-analysis': { title: 'Video Analysis', subtitle: 'Bus Footage → Detect Traffic Violations + Potholes → Bus Route → Challans / Repair' },
  '/map': { title: 'Live Map', subtitle: 'Unified Incident Map' },
  '/potholes': { title: 'Potholes', subtitle: 'Road Condition Monitoring' },
  '/traffic': { title: 'Traffic Violations', subtitle: 'Violation Detection & Management' },
  '/verification': { title: 'Verification Center', subtitle: 'Officer Verification Workflow' },
  '/challans': { title: 'Challans', subtitle: 'Fine & Challan Management' },
  '/repairs': { title: 'Repair Management', subtitle: 'Pothole Repair Tracking' },
  '/notifications': { title: 'Notifications', subtitle: 'System Alerts & Notices' },
  '/reports': { title: 'Reports & Analytics', subtitle: 'Data-Driven Insights' },
  '/settings': { title: 'Settings', subtitle: 'System Configuration' },
  '/demo': { title: 'Demo Mode', subtitle: 'Simulation & Testing' },
}

function getNotificationIcon(type) {
  switch (type) {
    case 'POTHOLE_DETECTED':
    case 'POTHOLE_VERIFICATION_NEEDED':
    case 'POTHOLE_VERIFIED':
    case 'POTHOLE_REPAIR_FINISHED':
    case 'POTHOLE_REPAIR_VERIFIED':
      return { icon: AlertTriangle, className: 'notification-type-icon pothole' }
    case 'VIOLATION_AI_VERIFIED':
    case 'VIOLATION_VERIFICATION_NEEDED':
    case 'VIOLATION_OFFICER_VERIFIED':
    case 'VIOLATION_REJECTED':
      return { icon: TrafficCone, className: 'notification-type-icon traffic' }
    case 'CHALLAN_GENERATED':
      return { icon: FileText, className: 'notification-type-icon challan' }
    default:
      return { icon: Bell, className: 'notification-type-icon system' }
  }
}

export default function Header({ notifications, onRefresh }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [showDropdown, setShowDropdown] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const dropdownRef = useRef(null)

  const page = pageTitles[location.pathname] || pageTitles['/']

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false)
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = notifications?.filter((n) => !n.is_read).length || 0

  const handleLogout = () => {
    setShowUserMenu(false)
    logout()
    navigate('/login', { replace: true })
  }

  const initials = (user?.name || user?.username || 'U')
    .split(' ')
    .map((s) => s[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <header className="header">
      <div className="header-title">
        <h1>{page.title}</h1>
        <p>{page.subtitle}</p>
      </div>

      <div className="header-actions" ref={dropdownRef}>
        <div style={{ position: 'relative' }}>
          <button
            className="btn btn-outline"
            onClick={() => setShowDropdown(!showDropdown)}
            style={{ position: 'relative' }}
          >
            <Bell size={16} />
            {unreadCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: -4,
                  right: -4,
                  background: '#ef4444',
                  color: 'white',
                  borderRadius: '50%',
                  width: 18,
                  height: 18,
                  fontSize: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                }}
              >
                {unreadCount}
              </span>
            )}
          </button>

          {showDropdown && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 48,
                width: 360,
                maxHeight: 480,
                overflowY: 'auto',
                background: 'white',
                borderRadius: 12,
                boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
                border: '1px solid #e2e8f0',
                zIndex: 200,
              }}
            >
              <div
                style={{
                  padding: '14px 16px',
                  borderBottom: '1px solid #e2e8f0',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontWeight: 700,
                }}
              >
                <span>Notifications</span>
                <button
                  onClick={() => navigate('/notifications')}
                  style={{ fontSize: 12, color: '#3b82f6', fontWeight: 600 }}
                >
                  View all
                </button>
              </div>
              {notifications.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>
                  <div style={{ fontSize: 32, marginBottom: 8 }}>🔔</div>
                  <div>No notifications</div>
                </div>
              ) : (
                notifications.map((n) => {
                  const { icon: Icon, className } = getNotificationIcon(n.notification_type)
                  return (
                    <div
                      key={n.id}
                      onClick={() => {
                        setShowDropdown(false)
                        if (n.related_entity_type === 'pothole') navigate('/potholes')
                        else if (n.related_entity_type === 'traffic_violation' || n.related_entity_type === 'challan') navigate('/traffic')
                      }}
                      style={{
                        padding: '12px 16px',
                        display: 'flex',
                        gap: 12,
                        cursor: 'pointer',
                        borderBottom: '1px solid #f1f5f9',
                        background: n.is_read ? 'white' : '#f0f6ff',
                      }}
                    >
                      <div className={className} style={{ flexShrink: 0 }}>
                        <Icon size={16} />
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>{n.title}</div>
                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{n.message}</div>
                        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                          {new Date(n.created_at).toLocaleString('en-IN')}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          )}
        </div>

        <button className="btn btn-primary btn-sm" onClick={onRefresh}>
          <MapPin size={14} /> Refresh
        </button>

        <div style={{ position: 'relative' }}>
          <button
            className="user-chip"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            <span className="user-avatar">{initials}</span>
            <span className="user-chip-name">{user?.name || user?.username}</span>
            <ChevronDown size={14} />
          </button>

          {showUserMenu && (
            <div className="user-menu">
              <div className="user-menu-head">
                <div className="user-menu-name">{user?.name}</div>
                <div className="user-menu-role">{user?.role} · {user?.username}</div>
                <div className="user-menu-email">{user?.email}</div>
              </div>
              <button className="user-menu-item danger" onClick={handleLogout}>
                <LogOut size={16} /> Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}