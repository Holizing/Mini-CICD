import { Link, useLocation } from 'react-router-dom'

const Sidebar = () => {
  const location = useLocation()

  const menuItems = [
    { path: '/projects', label: 'Projects' },
  ]

  const isActive = (path) => {
    if (path === '/projects') {
      return location.pathname === '/' || location.pathname.startsWith('/projects')
    }
    return location.pathname.startsWith(path)
  }

  return (
    <aside style={{
      width: '240px',
      backgroundColor: '#111827',
      color: 'white',
      padding: '24px 0',
      minHeight: 'calc(100vh - 64px)',
    }}>
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              padding: '12px 24px',
              color: isActive(item.path) ? '#60a5fa' : '#d1d5db',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: '600',
              borderLeft: isActive(item.path) ? '3px solid #60a5fa' : '3px solid transparent',
              backgroundColor: isActive(item.path) ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            }}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
