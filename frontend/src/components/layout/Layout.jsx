import Sidebar from './Sidebar'
import Header from './Header'

export default function Layout({ children, stats, notifications, onRefresh }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Header notifications={notifications} onRefresh={onRefresh} />
        <div className="page-container">{children}</div>
      </main>
    </div>
  )
}