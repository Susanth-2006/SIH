import { useState, useEffect } from 'react'
import MapView from '../components/map/MapView'
import { LoadingState } from '../components/ui/Feedback'
import { Bus, AlertTriangle, ShieldAlert } from 'lucide-react'

const EMPTY_INCIDENTS = {
  fleet_markers: [],
  pothole_markers: [],
  violation_markers: [],
  routes: [],
}

export default function MapPage() {
  const [incidents, setIncidents] = useState(EMPTY_INCIDENTS)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [filters, setFilters] = useState({
    showFleet: true,
    showPotholes: true,
    showViolations: true,
    showRoutes: true,
  })

  useEffect(() => {
    loadIncidents()
  }, [])

  useEffect(() => {
    const interval = setInterval(loadIncidents, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadIncidents = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/map/incidents')
      if (!res.ok) throw new Error(`Backend returned ${res.status}`)
      const data = await res.json()
      if (!data || typeof data !== 'object') throw new Error('Backend returned invalid data')
      setIncidents({ ...EMPTY_INCIDENTS, ...data })
      setLoadError('')
    } catch (e) {
      console.error('Failed to load incidents', e)
      setLoadError('Map data server is unreachable. Showing last-known or empty data — retrying automatically.')
    } finally {
      setLoading(false)
    }
  }

  const toggleFilter = (key) => {
    setFilters((f) => ({ ...f, [key]: !f[key] }))
  }

  if (loading) return <LoadingState label="Loading map..." />

  const onMarkerClick = (marker) => {
    const latlng = { lat: marker.latitude, lng: marker.longitude }
    window.open(`https://www.google.com/maps?q=${marker.latitude},${marker.longitude}`, '_blank')
  }

  const counts = {
    fleet: incidents?.fleet_markers?.length || 0,
    potholes: incidents?.pothole_markers?.length || 0,
    violations: incidents?.violation_markers?.length || 0,
  }

  return (
    <div>
      {loadError && (
        <div
          style={{
            margin: '8px 16px 0',
            padding: '8px 14px',
            borderRadius: 8,
            background: '#fef2f2',
            border: '1px solid #fecaca',
            color: '#b91c1c',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {loadError}
        </div>
      )}
      <div className="map-container" style={{ height: 'calc(100vh - var(--header-height) - 56px)' }}>
        <MapView
          incidents={incidents}
          filters={filters}
          onMarkerClick={onMarkerClick}
          height="100%"
        />

        <div className="map-toolbar">
          <div className="map-filter-panel">
            <div className="map-filter-title">Layers</div>
            <div className="map-legend">
              <div
                className="map-legend-item"
                onClick={() => toggleFilter('showFleet')}
                style={{ opacity: filters.showFleet ? 1 : 0.4 }}
              >
                <div className="map-legend-dot" style={{ background: '#3b82f6' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>Fleet Vehicles</span>
                  <span style={{ color: '#64748b', fontWeight: 600 }}>{counts.fleet}</span>
                </div>
              </div>
              <div
                className="map-legend-item"
                onClick={() => toggleFilter('showPotholes')}
                style={{ opacity: filters.showPotholes ? 1 : 0.4 }}
              >
                <div className="map-legend-dot" style={{ background: '#f59e0b' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>Potholes</span>
                  <span style={{ color: '#64748b', fontWeight: 600 }}>{counts.potholes}</span>
                </div>
              </div>
              <div
                className="map-legend-item"
                onClick={() => toggleFilter('showViolations')}
                style={{ opacity: filters.showViolations ? 1 : 0.4 }}
              >
                <div className="map-legend-dot" style={{ background: '#ef4444' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>Traffic Violations</span>
                  <span style={{ color: '#64748b', fontWeight: 600 }}>{counts.violations}</span>
                </div>
              </div>
              <div
                className="map-legend-item"
                onClick={() => toggleFilter('showRoutes')}
                style={{ opacity: filters.showRoutes ? 1 : 0.4 }}
              >
                <div className="map-legend-line" style={{ background: '#4285F4' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>Fleet Routes</span>
                </div>
              </div>
            </div>
          </div>

          <div className="map-filter-panel">
            <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b' }}>
              <Bus size={12} style={{ display: 'inline', marginRight: 4 }} /> Blue = Fleet
            </div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', marginTop: 4 }}>
              <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4, color: '#f59e0b' }} /> Yellow/Green = Pothole
            </div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', marginTop: 4 }}>
              <ShieldAlert size={12} style={{ display: 'inline', marginRight: 4, color: '#ef4444' }} /> Red = Violation
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}