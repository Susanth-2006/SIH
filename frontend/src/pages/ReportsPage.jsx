import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
} from 'recharts'
import api from '../services/api'
import { LoadingState } from '../components/ui/Feedback'

const PIE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export default function ReportsPage() {
  const [stats, setStats] = useState(null)
  const [potholes, setPotholes] = useState([])
  const [violations, setViolations] = useState([])
  const [challans, setChallans] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    try {
      const [statsData, potholesData, violationsData, challansData] = await Promise.all([
        api.apiGet('/api/dashboard/statistics'),
        api.apiGet('/api/potholes?limit=500'),
        api.apiGet('/api/traffic/violations?limit=500'),
        api.apiGet('/api/challans?limit=500'),
      ])
      setStats(statsData)
      setPotholes(potholesData)
      setViolations(violationsData)
      setChallans(challansData)
    } catch (e) {
      console.error('Failed to load report data', e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <LoadingState label="Preparing reports..." />

  const potholeStatusData = [
    { name: 'Pending', value: stats.potholes_pending },
    { name: 'Verified', value: stats.potholes_verified },
    { name: 'Work Started', value: stats.potholes_work_started },
    { name: 'Work Finished', value: stats.potholes_work_finished },
    { name: 'Fixed', value: stats.potholes_fixed },
    { name: 'Repair Failed', value: stats.potholes_repair_failed },
  ].filter((d) => d.value > 0)

  const violationTypeCounts = {}
  violations.forEach((v) => {
    violationTypeCounts[v.violation_type] = (violationTypeCounts[v.violation_type] || 0) + 1
  })
  const violationTypeData = Object.entries(violationTypeCounts).map(([type, count]) => ({
    name: type.replace('_', ' '),
    value: count,
  }))

  const verificationData = [
    { name: 'AI Verified', value: stats.violations_ai_verified },
    { name: 'Pending Officer', value: stats.violations_pending },
    { name: 'Officer Verified', value: stats.violations_officer_verified },
    { name: 'Rejected', value: stats.violations_rejected },
  ].filter((d) => d.value > 0)

  const challanData = [
    { name: 'Generated', value: stats.challans_generated },
    { name: 'Paid', value: stats.challans_paid },
  ].filter((d) => d.value > 0)

  const fleetCoverage = [
    { name: 'Active', value: stats.fleet_active },
    { name: 'Offline', value: stats.fleet_offline },
  ]

  const violationByVehicle = {}
  violations.forEach((v) => {
    const key = v.detected_by_vehicle_id ? `Vehicle ${v.detected_by_vehicle_id}` : 'Unknown'
    violationByVehicle[key] = (violationByVehicle[key] || 0) + 1
  })
  const vehicleData = Object.entries(violationByVehicle).map(([name, value]) => ({ name, value }))

  const recentViolationsByDay = {}
  violations.forEach((v) => {
    const day = new Date(v.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
    recentViolationsByDay[day] = (recentViolationsByDay[day] || 0) + 1
  })
  const violationTimeline = Object.entries(recentViolationsByDay)
    .slice(-14)
    .map(([day, count]) => ({ day, count }))

  return (
    <div>
      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="chart-container">
          <div className="chart-title">Pothole Status Distribution</div>
          {potholeStatusData.length === 0 ? (
            <div className="empty-state" style={{ padding: 30 }}>No pothole data</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={potholeStatusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                  {potholeStatusData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-container">
          <div className="chart-title">Traffic Violations by Type</div>
          {violationTypeData.length === 0 ? (
            <div className="empty-state" style={{ padding: 30 }}>No violation data</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={violationTypeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#ef4444" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="chart-container">
          <div className="chart-title">Verification Outcome</div>
          {verificationData.length === 0 ? (
            <div className="empty-state" style={{ padding: 30 }}>No verification data</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={verificationData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {verificationData.map((_, i) => (
                    <Cell key={i} fill={['#22c55e', '#f59e0b', '#3b82f6', '#ef4444'][i % 4]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-container">
          <div className="chart-title">Incidents by Detecting Vehicle</div>
          {vehicleData.length === 0 ? (
            <div className="empty-state" style={{ padding: 30 }}>No vehicle incident data</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={vehicleData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="chart-container">
          <div className="chart-title">Challan Generation</div>
          {challanData.length === 0 ? (
            <div className="empty-state" style={{ padding: 30 }}>No challan data</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={challanData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  <Cell fill="#8b5cf6" />
                  <Cell fill="#22c55e" />
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-container">
          <div className="chart-title">Fleet Coverage</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={fleetCoverage} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                <Cell fill="#3b82f6" />
                <Cell fill="#ef4444" />
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="chart-container" style={{ marginBottom: 24 }}>
        <div className="chart-title">Violation Detection Timeline</div>
        {violationTimeline.length === 0 ? (
          <div className="empty-state" style={{ padding: 30 }}>No timeline data</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={violationTimeline}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Area type="monotone" dataKey="count" stroke="#ef4444" fill="rgba(239,68,68,0.15)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}