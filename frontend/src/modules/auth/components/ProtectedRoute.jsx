import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'


function ProtectedRoute() {
  const location = useLocation()
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <main style={styles.loadingPage}>
        <div aria-label="Loading session" role="status" style={styles.spinner} />
        <span style={styles.loadingText}>Checking session...</span>
      </main>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}

const styles = {
  loadingPage: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    backgroundColor: '#f3f4f6',
  },
  spinner: {
    width: '20px',
    height: '20px',
    border: '2px solid #cbd5e1',
    borderTopColor: '#2563eb',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  loadingText: {
    color: '#475569',
    fontSize: '14px',
    fontWeight: 600,
  },
}

export default ProtectedRoute
