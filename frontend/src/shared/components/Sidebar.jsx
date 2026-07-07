import { Link, useLocation } from 'react-router-dom'

function Sidebar() {
  const location = useLocation()
  const isActive = location.pathname === '/' || location.pathname.startsWith('/settings')

  return (
    <aside
      style={{
        width: '240px',
        minHeight: 'calc(100vh - 64px)',
        padding: '24px 0',
        color: '#ffffff',
        backgroundColor: '#111827',
      }}
    >
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <Link
          to="/settings"
          style={{
            padding: '12px 24px',
            color: isActive ? '#60a5fa' : '#d1d5db',
            textDecoration: 'none',
            fontSize: '14px',
            fontWeight: 700,
            borderLeft: isActive ? '3px solid #60a5fa' : '3px solid transparent',
            backgroundColor: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
          }}
        >
          Settings
        </Link>
      </nav>
    </aside>
  )
}

export default Sidebar
