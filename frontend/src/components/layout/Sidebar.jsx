import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Map as MapIcon,
  Bus,
  AlertTriangle,
  TrafficCone,
  ShieldAlert,
  FileText,
  Wrench,
  Bell,
  BarChart3,
  Settings,
  FlaskConical,
  Building2,
  Film,
} from 'lucide-react'

const navSections = [
  {
    title: 'Overview',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/video-analysis', label: 'Video Analysis', icon: Film },
      { to: '/map', label: 'Live Map', icon: MapIcon },
    ],
  },
  {
    title: 'Monitoring',
    items: [
      { to: '/fleet', label: 'Live Fleet', icon: Bus },
      { to: '/potholes', label: 'Potholes', icon: AlertTriangle },
      { to: '/traffic', label: 'Traffic Violations', icon: TrafficCone },
    ],
  },
  {
    title: 'Operations',
    items: [
      { to: '/verification', label: 'Verification Center', icon: ShieldAlert },
      { to: '/challans', label: 'Challans', icon: FileText },
      { to: '/repairs', label: 'Repair Management', icon: Wrench },
    ],
  },
  {
    title: 'System',
    items: [
      { to: '/notifications', label: 'Notifications', icon: Bell },
      { to: '/reports', label: 'Reports', icon: BarChart3 },
      { to: '/demo', label: 'Demo Mode', icon: FlaskConical },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <Building2 size={20} />
        </div>
        <div>
          <div className="brand-title">Urban Intelligence</div>
          <div className="brand-subtitle">Command Center</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navSections.map((section) => (
          <div key={section.title}>
            <div className="nav-section-title">{section.title}</div>
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'active' : ''}`
                }
              >
                <item.icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div>Urban Intelligence Platform</div>
        <div>v1.0.0</div>
      </div>
    </aside>
  )
}