import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { Alert } from '../components/ui/Feedback'
import { Play, MapPin, Database, FlaskConical, RefreshCw, Video, ArrowRight } from 'lucide-react'

export default function DemoModePage({ onRefresh }) {
  const [vehicles, setVehicles] = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState('')
  const [simulation, setSimulation] = useState({ startLat: 17.385, startLng: 78.4867, endLat: 17.395, endLng: 78.4967 })
  const [message, setMessage] = useState('')
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    loadVehicles()
  }, [])

  const loadVehicles = async () => {
    try {
      const data = await api.apiGet('/api/fleet/')
      setVehicles(data)
      if (data.length > 0) setSelectedVehicle(String(data[0].id))
    } catch (e) {
      console.error('Failed to load vehicles', e)
    }
  }

  const seedDemoData = async () => {
    setProcessing(true)
    try {
      const res = await api.apiPost('/api/demo/seed', {})
      setMessage(res.detail || 'Demo data seeded successfully')
      loadVehicles()
      if (onRefresh) onRefresh()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setProcessing(false)
    }
  }

  const simulateFleet = async () => {
    setProcessing(true)
    setMessage('')
    try {
      if (!selectedVehicle) {
        setMessage('Error: Select a fleet vehicle first')
        setProcessing(false)
        return
      }
      await api.apiPost('/api/demo/simulate-fleet', {
        vehicle_id: parseInt(selectedVehicle),
        start_lat: parseFloat(simulation.startLat),
        start_lng: parseFloat(simulation.startLng),
        end_lat: parseFloat(simulation.endLat),
        end_lng: parseFloat(simulation.endLng),
        num_points: 30,
      })
      setMessage(`Simulated GPS route for vehicle ${selectedVehicle}`)
      if (onRefresh) onRefresh()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setProcessing(false)
    }
  }

  const addPothole = async () => {
    setProcessing(true)
    try {
      await api.apiPost('/api/demo/add-pothole', {
        latitude: parseFloat(simulation.startLat),
        longitude: parseFloat(simulation.startLng),
        severity: 'high',
        confidence: 0.91,
        detected_by_vehicle_id: selectedVehicle ? parseInt(selectedVehicle) : null,
      })
      setMessage('Demo pothole created (91% confidence, auto-verified)')
      if (onRefresh) onRefresh()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setProcessing(false)
    }
  }

  const addViolation = async () => {
    setProcessing(true)
    try {
      await api.apiPost('/api/demo/add-violation', {
        violation_type: 'NO_HELMET',
        vehicle_number: 'DEMO-VEHICLE',
        latitude: parseFloat(simulation.startLat),
        longitude: parseFloat(simulation.startLng),
        confidence: 0.94,
        detected_by_vehicle_id: selectedVehicle ? parseInt(selectedVehicle) : null,
      })
      setMessage('Demo violation created (94% confidence, AI verified, challan generated)')
      if (onRefresh) onRefresh()
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div>
      <div className="demo-banner">
        <FlaskConical size={20} />
        <span>DEMO MODE — All data generated here is simulated and clearly identifiable as demo data.</span>
      </div>

      {message && <Alert type={message.startsWith('Error') ? 'error' : 'success'}>{message}</Alert>}

      <div className="filters-bar">
        <div className="filter-group">
          <label>Fleet Vehicle</label>
          <select className="filter-select" value={selectedVehicle} onChange={(e) => setSelectedVehicle(e.target.value)}>
            <option value="">Select vehicle</option>
            {vehicles.map((v) => (
              <option key={v.id} value={v.id}>{v.fleet_id} - {v.vehicle_number}</option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" onClick={seedDemoData} disabled={processing}>
          <Database size={16} /> Seed Demo Data
        </button>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className="stat-icon accent"><MapPin size={18} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>GPS Simulation</div>
              <div className="text-muted" style={{ fontSize: 12 }}>Simulate fleet movement along GPS route</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div className="filter-group">
              <label>Start Lat</label>
              <input
                className="filter-input"
                type="number"
                step="0.0001"
                value={simulation.startLat}
                onChange={(e) => setSimulation({ ...simulation, startLat: e.target.value })}
              />
            </div>
            <div className="filter-group">
              <label>Start Lng</label>
              <input
                className="filter-input"
                type="number"
                step="0.0001"
                value={simulation.startLng}
                onChange={(e) => setSimulation({ ...simulation, startLng: e.target.value })}
              />
            </div>
            <div className="filter-group">
              <label>End Lat</label>
              <input
                className="filter-input"
                type="number"
                step="0.0001"
                value={simulation.endLat}
                onChange={(e) => setSimulation({ ...simulation, endLat: e.target.value })}
              />
            </div>
            <div className="filter-group">
              <label>End Lng</label>
              <input
                className="filter-input"
                type="number"
                step="0.0001"
                value={simulation.endLng}
                onChange={(e) => setSimulation({ ...simulation, endLng: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <button className="btn btn-primary" onClick={simulateFleet} disabled={processing}>
              <Play size={16} /> Simulate Route
            </button>
            <button className="btn btn-outline" onClick={addPothole} disabled={processing}>
              <MapPin size={16} /> Add Demo Pothole
            </button>
          </div>
          <div style={{ marginTop: 10 }}>
            <button className="btn btn-outline" style={{ width: '100%' }} onClick={addViolation} disabled={processing}>
              <RefreshCw size={16} /> Add Demo Violation
            </button>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div className="stat-icon warning"><Video size={18} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>Video Analysis Pipeline</div>
              <div className="text-muted" style={{ fontSize: 12 }}>Pick a bus-camera video → traffic + pothole detection → evidence → challans / verification / repair</div>
            </div>
          </div>

          <div className="alert alert-info">
            <Video size={16} />
            <span>
              The <strong>Video Analysis</strong> page handles bus-footage processing (no uploads) with live progress, evidence viewer, and the full confidence workflow.
            </span>
          </div>

          <Link to="/video-analysis" className="btn btn-primary" style={{ marginTop: 12 }}>
            Open Video Analysis <ArrowRight size={16} />
          </Link>

          <div className="text-muted" style={{ fontSize: 12, marginTop: 12, lineHeight: 1.5 }}>
            Flow: Select bus footage → sample frames → run traffic + pothole detection → merge duplicate detections into events → pick best evidence frame → record bus route on the map → confidence ≥ 80% auto-verifies and generates challans / routes potholes to repair → below 80% goes to the Verification Center.
          </div>
        </div>
      </div>

      <div className="alert alert-warning" style={{ marginTop: 24 }}>
        <Database size={16} />
        <span>
          Demo pipeline end-to-end flow: Video Analysis → AI detection → Violation classification → Confidence scoring → GPS synchronization → Event creation → Database → Map → Officer dashboard → Challans → Pothole repair.
        </span>
      </div>
    </div>
  )
}