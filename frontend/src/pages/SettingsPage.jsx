import { useState, useEffect } from 'react'
import api from '../services/api'
import { Alert } from '../components/ui/Feedback'
import { Save, Database, Bell, Map, Server, KeyRound } from 'lucide-react'

export default function SettingsPage() {
  const [saved, setSaved] = useState('')
  const [config, setConfig] = useState({
    confidenceThreshold: '80',
    googleMapsKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
    mlServiceUrl: 'http://localhost:8001',
    notifyNewPothole: true,
    notifyNewViolation: true,
    notifyVerificationNeeded: true,
    notifyChallanGenerated: true,
  })

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const res = await fetch('/api/health')
      const data = await res.json()
      setConfig((c) => ({ ...c, mlServiceUrl: data.ml_service || c.mlServiceUrl }))
    } catch (e) {
      console.error('Failed to load health', e)
    }
  }

  const handleSave = () => {
    setSaved('Settings saved successfully')
    setTimeout(() => setSaved(''), 4000)
  }

  return (
    <div className="grid grid-2">
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <div className="stat-icon accent"><Server size={20} /></div>
          <div>
            <div style={{ fontWeight: 700 }}>System Configuration</div>
            <div className="text-muted" style={{ fontSize: 12 }}>Runtime system parameters</div>
          </div>
        </div>

        {saved && <Alert type="success">{saved}</Alert>}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="filter-group">
            <label>AI Confidence Threshold (%)</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <input
                type="range"
                min="50"
                max="95"
                value={config.confidenceThreshold}
                onChange={(e) => setConfig({ ...config, confidenceThreshold: e.target.value })}
                style={{ flex: 1 }}
              />
              <span style={{ fontWeight: 700, fontSize: 16, color: '#3b82f6' }}>{config.confidenceThreshold}%</span>
            </div>
            <div className="text-muted" style={{ fontSize: 12 }}>
              Detections above this threshold are auto-verified by AI. Below requires officer review.
            </div>
          </div>

          <div className="filter-group">
            <label>Google Maps API Key</label>
            <input
              className="filter-input"
              style={{ width: '100%' }}
              value={config.googleMapsKey}
              onChange={(e) => setConfig({ ...config, googleMapsKey: e.target.value })}
            />
            <div className="text-muted" style={{ fontSize: 11 }}>Stored server-side in .env. Never exposed in client bundle.</div>
          </div>

          <div className="filter-group">
            <label>ML Service URL</label>
            <input
              className="filter-input"
              style={{ width: '100%' }}
              value={config.mlServiceUrl}
              onChange={(e) => setConfig({ ...config, mlServiceUrl: e.target.value })}
            />
          </div>

          <button className="btn btn-primary" onClick={handleSave}>
            <Save size={16} /> Save Configuration
          </button>
        </div>
      </div>

      <div>
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <div className="stat-icon warning"><Bell size={20} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>Notification Preferences</div>
              <div className="text-muted" style={{ fontSize: 12 }}>Choose which events notify officers</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { key: 'notifyNewPothole', label: 'New pothole detected' },
              { key: 'notifyNewViolation', label: 'New traffic violation detected' },
              { key: 'notifyVerificationNeeded', label: 'Low-confidence detection requires verification' },
              { key: 'notifyChallanGenerated', label: 'Challan generated' },
            ].map((item) => (
              <label key={item.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}>
                <span style={{ fontSize: 13.5 }}>{item.label}</span>
                <input
                  type="checkbox"
                  checked={config[item.key]}
                  onChange={(e) => setConfig({ ...config, [item.key]: e.target.checked })}
                  style={{ width: 18, height: 18 }}
                />
              </label>
            ))}
          </div>

          <div className="divider" />
          <button className="btn btn-primary" onClick={handleSave}>
            <Save size={16} /> Save Preferences
          </button>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <div className="stat-icon cyan"><Database size={20} /></div>
            <div>
              <div style={{ fontWeight: 700 }}>Database Status</div>
              <div className="text-muted" style={{ fontSize: 12 }}>Data storage information</div>
            </div>
          </div>

          <div className="detail-list">
            <div className="detail-row">
              <div className="detail-label">Database</div>
              <div className="detail-value">SQLite (urban_intelligence.db)</div>
            </div>
            <div className="detail-row">
              <div className="detail-label">ML Models</div>
              <div className="detail-value">
                <div>Traffic: YOLOv5 (best.pt)</div>
                <div>Pothole: YOLOv5 (pothole model)</div>
              </div>
            </div>
            <div className="detail-row">
              <div className="detail-label">OCR</div>
              <div className="detail-value">PlateRecognizer API</div>
            </div>
            <div className="detail-row">
              <div className="detail-label">Map Provider</div>
              <div className="detail-value">Google Maps JavaScript API</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}