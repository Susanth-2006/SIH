import { useEffect, useState } from 'react'
import api from '../services/api'
import { LoadingState, EmptyState } from '../components/ui/Feedback'
import { StatusBadge, formatDate, confidencePct, POTHOLE_STATUS_CONFIG } from '../utils/helpers'
import { Bus, MapPin, Camera, Satellite, Plus, Radio, Route as RouteIcon } from 'lucide-react'

export default function LiveFleet() {
  const [vehicles, setVehicles] = useState([])
  const [routes, setRoutes] = useState({})
  const [loading, setLoading] = useState(true)
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [filter, setFilter] = useState('ALL')

  useEffect(() => {
    loadFleet()
    const interval = setInterval(loadFleet, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedVehicle) {
      loadRoute(selectedVehicle.id)
    }
  }, [selectedVehicle])

  const loadFleet = async () => {
    try {
      const data = await api.apiGet('/api/fleet/')
      setVehicles(data)
    } catch (e) {
      console.error('Failed to load fleet', e)
    } finally {
      setLoading(false)
    }
  }

  const loadRoute = async (id) => {
    try {
      const data = await api.apiGet(`/api/fleet/${id}/route?limit=100`)
      setRoutes((r) => ({ ...r, [id]: data }))
    } catch (e) {
      console.error('Failed to load route', e)
    }
  }

  const filtered = filter === 'ALL' ? vehicles : vehicles.filter((v) => {
    if (filter === 'ACTIVE') return v.is_active && v.gps_status === 'active'
    if (filter === 'OFFLINE') return !(v.is_active && v.gps_status === 'active')
    return true
  })

  const activeCount = vehicles.filter((v) => v.is_active && v.gps_status === 'active').length
  const offlineCount = vehicles.length - activeCount

  const cameraStatus = (s) => {
    const config = {
      active: { label: 'Camera Online', color: '#22c55e' },
      inactive: { label: 'Camera Off', color: '#94a3b8' },
      error: { label: 'Camera Error', color: '#ef4444' },
    }
    const c = config[s] || config.inactive
    return <span className="status-badge" style={{ color: c.color, backgroundColor: `${c.color}15`, borderColor: `${c.color}33` }}>{c.label}</span>
  }

  const gpsStatus = (s) => {
    const config = {
      active: { label: 'GPS Online', color: '#22c55e' },
      offline: { label: 'GPS Offline', color: '#ef4444' },
      inactive: { label: 'GPS Inactive', color: '#94a3b8' },
    }
    const c = config[s] || config.inactive
    return <span className="status-badge" style={{ color: c.color, backgroundColor: `${c.color}15`, borderColor: `${c.color}33` }}>{c.label}</span>
  }

  return (
    <div>
      <div className="filters-bar">
        <div className="filter-group">
          <label>Status</label>
          <select className="filter-select" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="ALL">All Vehicles</option>
            <option value="ACTIVE">Active</option>
            <option value="OFFLINE">Offline</option>
          </select>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
          <div className="card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Radio size={16} color="#22c55e" />
            <span style={{ fontWeight: 700 }}>{activeCount}</span>
            <span className="text-muted" style={{ fontSize: 12 }}>active</span>
          </div>
          <div className="card" style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Radio size={16} color="#ef4444" />
            <span style={{ fontWeight: 700 }}>{offlineCount}</span>
            <span className="text-muted" style={{ fontSize: 12 }}>offline</span>
          </div>
          <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            <Plus size={16} /> Add Vehicle
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingState label="Loading fleet data..." />
      ) : filtered.length === 0 ? (
        <EmptyState icon="🚌" title="No fleet vehicles" description="Register vehicles via the Add Vehicle button or seed demo data." />
      ) : (
        <div className="grid grid-3">
          {filtered.map((v) => (
            <div
              className="card"
              key={v.id}
              style={{ cursor: 'pointer', borderColor: selectedVehicle?.id === v.id ? '#3b82f6' : undefined }}
              onClick={() => setSelectedVehicle(selectedVehicle?.id === v.id ? null : v)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div
                    style={{
                      width: 42,
                      height: 42,
                      borderRadius: 10,
                      background: 'rgba(59,130,246,0.12)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Bus size={20} color="#3b82f6" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700 }}>{v.fleet_id}</div>
                    <div className="text-muted" style={{ fontSize: 12 }}>{v.vehicle_number}</div>
                  </div>
                </div>
                <span
                  className="status-badge"
                  style={{
                    color: v.gps_status === 'active' ? '#22c55e' : '#ef4444',
                    backgroundColor: v.gps_status === 'active' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                    borderColor: 'transparent',
                  }}
                >
                  {v.gps_status === 'active' ? '● LIVE' : '● OFFLINE'}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                  <MapPin size={14} color="#64748b" />
                  <span className="text-muted">Location:</span>
                  <span style={{ fontWeight: 500 }}>
                    {v.current_lat ? `${v.current_lat.toFixed(5)}, ${v.current_lng.toFixed(5)}` : 'Not tracked'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                  <RouteIcon size={14} color="#64748b" />
                  <span className="text-muted">Route:</span>
                  <span style={{ fontWeight: 500 }}>{v.route_name || 'Unassigned'}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                  <Camera size={14} color="#64748b" />
                  <span className="text-muted">Camera:</span>
                  {cameraStatus(v.camera_status)}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                  <Satellite size={14} color="#64748b" />
                  <span className="text-muted">GPS:</span>
                  {gpsStatus(v.gps_status)}
                </div>
              </div>

              <div className="divider" style={{ margin: '12px 0' }} />

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, color: '#94a3b8' }}>
                <span>Last updated: {formatDate(v.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedVehicle && (
        <div
          style={{ position: 'fixed', top: 80, right: 28, width: 360, background: 'white', borderRadius: 12, boxShadow: '0 20px 60px rgba(0,0,0,0.15)', border: '1px solid #e2e8f0', zIndex: 300, maxHeight: '80vh', overflow: 'auto' }}
        >
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 700 }}>{selectedVehicle.fleet_id} — {selectedVehicle.vehicle_number}</div>
              <div className="text-muted" style={{ fontSize: 12 }}>{selectedVehicle.route_name}</div>
            </div>
            <button className="close-btn" onClick={() => setSelectedVehicle(null)}>×</button>
          </div>
          <div style={{ padding: 16 }}>
            {selectedVehicle.current_lat && (
              <div style={{ marginBottom: 12, fontSize: 13 }}>
                <div className="text-muted" style={{ marginBottom: 4 }}>GPS Coordinates</div>
                <div style={{ fontWeight: 600 }}>
                  {selectedVehicle.current_lat.toFixed(5)}, {selectedVehicle.current_lng.toFixed(5)}
                </div>
              </div>
            )}
            <div className="tracking-route">
              <div className="text-muted" style={{ fontSize: 12, marginBottom: 4 }}>Route History</div>
              {routes[selectedVehicle.id]?.length ? (
                routes[selectedVehicle.id].slice(-8).map((p) => (
                  <div className="tracking-point" key={p.id}>
                    <div className="tracking-dot" />
                    <span>{p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}</span>
                    <span className="text-muted" style={{ fontSize: 11 }}>
                      {new Date(p.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-muted" style={{ fontSize: 12 }}>No GPS history recorded</div>
              )}
            </div>
          </div>
        </div>
      )}

      {showAddModal && (
        <AddVehicleModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => {
            setShowAddModal(false)
            loadFleet()
          }}
        />
      )}
    </div>
  )
}

function AddVehicleModal({ onClose, onAdded }) {
  const [form, setForm] = useState({ fleet_id: '', vehicle_number: '', vehicle_type: 'bus', route_name: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await api.apiPost('/api/fleet/', form)
      onAdded()
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 420 }}>
        <div className="modal-header">
          <h3 className="modal-title">Register Fleet Vehicle</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="filter-group">
              <label>Fleet ID</label>
              <input
                className="filter-input"
                style={{ width: '100%' }}
                value={form.fleet_id}
                onChange={(e) => setForm({ ...form, fleet_id: e.target.value })}
                placeholder="e.g. F-106"
                required
              />
            </div>
            <div className="filter-group">
              <label>Vehicle Number</label>
              <input
                className="filter-input"
                style={{ width: '100%' }}
                value={form.vehicle_number}
                onChange={(e) => setForm({ ...form, vehicle_number: e.target.value })}
                placeholder="e.g. TS09KL4321"
                required
              />
            </div>
            <div className="filter-group">
              <label>Vehicle Type</label>
              <select
                className="filter-select"
                style={{ width: '100%' }}
                value={form.vehicle_type}
                onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })}
              >
                <option value="bus">Bus</option>
                <option value="van">Van</option>
                <option value="car">Car</option>
                <option value="truck">Truck</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Route</label>
              <input
                className="filter-input"
                style={{ width: '100%' }}
                value={form.route_name}
                onChange={(e) => setForm({ ...form, route_name: e.target.value })}
                placeholder="e.g. Route F - Central"
              />
            </div>
            {error && <div className="alert alert-error">{error}</div>}
          </div>
        </form>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Adding...' : 'Add Vehicle'}
          </button>
        </div>
      </div>
    </div>
  )
}