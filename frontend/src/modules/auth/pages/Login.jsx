import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'


function getLoginError(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  return 'Could not sign in. Check that the API server is running.'
}

function Login() {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, loading, login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const previousLocation = location.state?.from
  const destination = previousLocation
    ? `${previousLocation.pathname}${previousLocation.search || ''}${previousLocation.hash || ''}`
    : '/'

  if (loading) {
    return (
      <main style={styles.loadingPage}>
        <div aria-label="Loading session" role="status" style={styles.spinner} />
        <span style={styles.loadingText}>Checking session...</span>
      </main>
    )
  }

  if (isAuthenticated) {
    return <Navigate to={destination} replace />
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (!username.trim() || !password) {
      setError('Username and password are required')
      return
    }

    setSubmitting(true)
    try {
      await login(username, password)
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(getLoginError(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main style={styles.page}>
      <section style={styles.loginPanel} aria-labelledby="login-title">
        <div style={styles.brand}>
          <span style={styles.brandMark}>CI</span>
          <span>Mini CI/CD</span>
        </div>

        <div style={styles.heading}>
          <h1 id="login-title" style={styles.title}>Sign in</h1>
          <p style={styles.subtitle}>Use your administrator account.</p>
        </div>

        {error && <div role="alert" style={styles.error}>{error}</div>}

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.field}>
            <span style={styles.label}>Username</span>
            <input
              autoComplete="username"
              autoFocus
              disabled={submitting}
              maxLength="100"
              onChange={(event) => setUsername(event.target.value)}
              required
              style={styles.input}
              value={username}
            />
          </label>

          <label style={styles.field}>
            <span style={styles.label}>Password</span>
            <input
              autoComplete="current-password"
              disabled={submitting}
              maxLength="128"
              onChange={(event) => setPassword(event.target.value)}
              required
              style={styles.input}
              type="password"
              value={password}
            />
          </label>

          <button disabled={submitting} style={styles.submitButton} type="submit">
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}

const styles = {
  loadingPage: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    backgroundColor: '#e9eef5',
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
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    backgroundColor: '#e9eef5',
  },
  loginPanel: {
    width: '100%',
    maxWidth: '420px',
    border: '1px solid #dbe2ea',
    borderRadius: '8px',
    padding: '32px',
    backgroundColor: '#ffffff',
    boxShadow: '0 16px 40px rgba(15, 23, 42, 0.10)',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    color: '#0f172a',
    fontSize: '15px',
    fontWeight: 800,
  },
  brandMark: {
    width: '32px',
    height: '32px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '6px',
    color: '#ffffff',
    backgroundColor: '#2563eb',
    fontSize: '12px',
  },
  heading: {
    margin: '30px 0 22px',
  },
  title: {
    margin: 0,
    color: '#111827',
    fontSize: '28px',
    lineHeight: 1.2,
  },
  subtitle: {
    margin: '8px 0 0',
    color: '#64748b',
    fontSize: '14px',
  },
  error: {
    marginBottom: '18px',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    padding: '11px 12px',
    color: '#991b1b',
    backgroundColor: '#fef2f2',
    fontSize: '14px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    color: '#334155',
    fontSize: '13px',
    fontWeight: 700,
  },
  input: {
    width: '100%',
    minHeight: '44px',
    border: '1px solid #cbd5e1',
    borderRadius: '6px',
    padding: '10px 12px',
    color: '#0f172a',
    backgroundColor: '#ffffff',
    outlineColor: '#2563eb',
  },
  submitButton: {
    width: '100%',
    minHeight: '44px',
    marginTop: '4px',
    border: 0,
    borderRadius: '6px',
    color: '#ffffff',
    backgroundColor: '#2563eb',
    fontWeight: 800,
  },
}

export default Login
