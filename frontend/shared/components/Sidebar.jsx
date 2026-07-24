import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const Sidebar = () => {
  const location = useLocation()

  const menuItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/build', label: 'Build', icon: '🔨' },
    { path: '/deploy', label: 'Deploy', icon: '🚀' },
    { path: '/history', label: 'History', icon: '📜' },
  ]

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <aside style={{
      width: '240px',
      backgroundColor: '#111827',
      color: 'white',
      padding: '24px 0',
      display: 'flex',
      flexDirection: 'column',
      minHeight: 'calc(100vh - 64px)'
    }}>
      <nav style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '12px 24px',
              color: isActive(item.path) ? '#60a5fa' : '#9ca3af',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'all 0.2s',
              borderLeft: isActive(item.path) ? '3px solid #60a5fa' : '3px solid transparent',
              backgroundColor: isActive(item.path) ? 'rgba(59, 130, 246, 0.1)' : 'transparent'
            }}
            onMouseEnter={(e) => {
              if (!isActive(item.path)) {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)'
                e.currentTarget.style.color = 'white'
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive(item.path)) {
                e.currentTarget.style.backgroundColor = 'transparent'
                e.currentTarget.style.color = '#9ca3af'
              }
            }}
          >
            <span style={{ fontSize: '18px' }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
