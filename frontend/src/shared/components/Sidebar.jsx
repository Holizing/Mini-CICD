import { Link, useLocation } from 'react-router-dom'


const MENU_ITEMS = [
  { path: '/', label: 'Dashboard' },
  { path: '/projects', label: 'Projects' },
  { path: '/build', label: 'Build' },
  { path: '/deploy', label: 'Deploy' },
  { path: '/history', label: 'History' },
  { path: '/automation', label: 'Automation' },
  { path: '/settings', label: 'Settings' },
]

function Sidebar() {
  const location = useLocation()

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <aside
      className="app-sidebar"
      style={{
        width: '240px',
        minHeight: 'calc(100vh - 64px)',
        padding: '24px 0',
        color: '#ffffff',
        backgroundColor: '#111827',
      }}
    >
      <nav className="app-sidebar__nav" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {MENU_ITEMS.map((item) => {
          const active = isActive(item.path)
          return (
            <Link
              className="app-sidebar__link"
              key={item.path}
              to={item.path}
              style={{
                padding: '12px 24px',
                color: active ? '#60a5fa' : '#d1d5db',
                textDecoration: 'none',
                fontSize: '14px',
                fontWeight: 700,
                borderLeft: active ? '3px solid #60a5fa' : '3px solid transparent',
                borderBottomColor: active ? '#60a5fa' : 'transparent',
                backgroundColor: active ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
              }}
            >
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

export default Sidebar
