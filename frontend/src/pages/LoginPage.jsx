import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ShieldCheck, User, Lock, Mountain, Truck, AlertTriangle, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const from = location.state?.from?.pathname || '/'

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || !password) {
      setError('Enter username and password')
      return
    }
    setError('')
    setBusy(true)
    try {
      await login(username.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  const quickFill = (u, p) => {
    setUsername(u)
    setPassword(p)
    setError('')
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="login-logo"><ShieldCheck size={26} /></div>
          <h1 className="login-title">Urban Intelligence Platform</h1>
          <p className="login-subtitle">Traffic fines, pothole repair, and fleet monitoring — in one control room.</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="alert alert-error">
              <AlertTriangle size={15} />
              {error}
            </div>
          )}
          <label className="login-label">Username</label>
          <div className="login-field">
            <User size={16} />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin"
              autoFocus
              autoComplete="username"
            />
          </div>

          <label className="login-label">Password</label>
          <div className="login-field">
            <Lock size={16} />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          <button className="btn btn-primary login-submit" type="submit" disabled={busy}>
            {busy ? <Loader2 size={16} className="spin-svg" /> : <ShieldCheck size={16} />}
            {busy ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="login-demo">
          <div className="login-demo-title">Demo Accounts</div>
          <div className="login-demo-row">
            <span><Mountain size={13} /> Admin</span>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => quickFill('admin', 'admin123')}
            >
              admin / admin123
            </button>
          </div>
          <div className="login-demo-row">
            <span><Truck size={13} /> Officer</span>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => quickFill('officer1', 'officer123')}
            >
              officer1 / officer123
            </button>
          </div>
        </div>

        <div className="login-footer">
          <Link to="/">Return to platform</Link> · Urban Intelligence v1.0.0
        </div>
      </div>
    </div>
  )
}