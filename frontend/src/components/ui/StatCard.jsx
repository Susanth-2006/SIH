import { useState } from 'react'

export default function StatCard({ label, value, icon, variant = 'accent' }) {
  return (
    <div className={`stat-card ${variant}`}>
      <div className={`stat-icon ${variant}`}>{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

export function StatsGrid({ children }) {
  return <div className="grid grid-4">{children}</div>
}

export function StatCardGroup({ stats }) {
  if (!stats) return null
  return (
    <div className="grid grid-4">
      {stats.map((s) => (
        <StatCard key={s.label} label={s.label} value={s.value} icon={s.icon} variant={s.variant} />
      ))}
    </div>
  )
}