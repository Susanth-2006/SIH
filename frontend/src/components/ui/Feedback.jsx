export function LoadingState({ label = 'Loading...' }) {
  return (
    <div className="loading-spinner">
      <div>
        <div className="spinner" style={{ margin: '0 auto 12px' }} />
        <div style={{ textAlign: 'center', color: '#64748b', fontSize: 13 }}>{label}</div>
      </div>
    </div>
  )
}

export function EmptyState({ icon = '📭', title = 'No data found', description = 'No records match your criteria.' }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <div className="empty-state-title">{title}</div>
      <div>{description}</div>
    </div>
  )
}

export function Alert({ type = 'success', children }) {
  return <div className={`alert alert-${type}`}>{children}</div>
}