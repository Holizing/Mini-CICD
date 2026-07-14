import { useLocation } from 'react-router-dom'

import { useAuth } from '../../modules/auth/context/AuthContext'

function Navbar() {
  const location = useLocation()
  const { user, logout } = useAuth()
  const pageTitle = location.pathname.startsWith('/settings') || location.pathname === '/' ? 'Settings' : 'Mini CI/CD'

  return (
    <header
      className="app-navbar"
      style={{
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        color: '#ffffff',
        backgroundColor: '#0f172a',
      }}
    >
      <strong style={{ fontSize: '18px' }}>Mini CI/CD</strong>
      <div className="app-navbar__account" style={styles.accountArea}>
        <span className="app-navbar__page-title" style={styles.pageTitle}>{pageTitle}</span>
        <span aria-hidden="true" className="app-navbar__divider" style={styles.divider} />
        <span className="app-navbar__username" style={styles.username}>{user?.username}</span>
        <button type="button" onClick={logout} style={styles.logoutButton}>
          Log out
        </button>
      </div>
    </header>
  )
}

const styles = {
  accountArea: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    minWidth: 0,
  },
  pageTitle: {
    color: '#cbd5e1',
    fontSize: '13px',
  },
  divider: {
    width: '1px',
    height: '20px',
    backgroundColor: '#334155',
  },
  username: {
    maxWidth: '160px',
    overflow: 'hidden',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: 700,
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  logoutButton: {
    minHeight: '34px',
    border: '1px solid #475569',
    borderRadius: '6px',
    padding: '0 12px',
    color: '#e2e8f0',
    backgroundColor: 'transparent',
    fontSize: '13px',
    fontWeight: 700,
  },
}

export default Navbar
