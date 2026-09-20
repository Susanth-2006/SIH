import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/layout/Layout'
import RequireAuth from './components/auth/RequireAuth'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import LiveFleet from './pages/LiveFleet'
import MapPage from './pages/MapPage'
import PotholesPage from './pages/PotholesPage'
import TrafficViolationsPage from './pages/TrafficViolationsPage'
import VerificationCenter from './pages/VerificationCenter'
import ChallansPage from './pages/ChallansPage'
import RepairManagement from './pages/RepairManagement'
import NotificationsPage from './pages/NotificationsPage'
import ReportsPage from './pages/ReportsPage'
import SettingsPage from './pages/SettingsPage'
import DemoModePage from './pages/DemoModePage'
import VideoAnalysisPage from './pages/VideoAnalysisPage'
import api from './services/api'

export default function App() {
  const [notifications, setNotifications] = useState([])
  const [stats, setStats] = useState(null)

  useEffect(() => {
    loadStats()
    loadNotifications()
  }, [])

  const loadStats = async () => {
    try {
      const data = await api.apiGet('/api/dashboard/statistics')
      setStats(data)
    } catch (e) {
      console.error('Failed to load stats', e)
    }
  }

  const loadNotifications = async () => {
    try {
      const data = await api.apiGet('/api/notifications/')
      setNotifications(data.slice(0, 8))
    } catch (e) {
      console.error('Failed to load notifications', e)
    }
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout stats={stats} notifications={notifications} onRefresh={loadStats}>
              <Routes>
                <Route path="/" element={<Dashboard stats={stats} onRefresh={loadStats} />} />
                <Route path="/fleet" element={<LiveFleet />} />
                <Route path="/map" element={<MapPage />} />
                <Route path="/video-analysis" element={<VideoAnalysisPage onRefresh={loadStats} />} />
                <Route path="/potholes" element={<PotholesPage />} />
                <Route path="/traffic" element={<TrafficViolationsPage />} />
                <Route path="/verification" element={<VerificationCenter />} />
                <Route path="/challans" element={<ChallansPage />} />
                <Route path="/repairs" element={<RepairManagement />} />
                <Route path="/notifications" element={<NotificationsPage onRefresh={loadNotifications} />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/demo" element={<DemoModePage onRefresh={loadStats} />} />
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  )
}