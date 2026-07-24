import { useEffect, useMemo, useState } from 'react'

import { settingsService } from '../services/settingsService'

const INITIAL_FORM = {
  workspace_dir: '',
  logs_dir: '',
  default_branch: '',
  default_deploy_path: '',
  default_service_name: '',
  build_timeout_seconds: 600,
  deploy_timeout_seconds: 600,
  auto_deploy_enabled: false,
  docker_enabled: true,
  webhook_secret: '',
  webhook_secret_configured: false,
}

const timeoutFields = ['build_timeout_seconds', 'deploy_timeout_seconds']

function normalizeSettings(settings) {
  return {
    workspace_dir: settings.workspace_dir || '',
    logs_dir: settings.logs_dir || '',
    default_branch: settings.default_branch || '',
    default_deploy_path: settings.default_deploy_path || '',
    default_service_name: settings.default_service_name || '',
    build_timeout_seconds: settings.build_timeout_seconds || 600,
    deploy_timeout_seconds: settings.deploy_timeout_seconds || 600,
    auto_deploy_enabled: Boolean(settings.auto_deploy_enabled),
    docker_enabled: Boolean(settings.docker_enabled),
    webhook_secret: '',
    webhook_secret_configured: Boolean(settings.webhook_secret_configured),
  }
}

function getErrorMessage(err, fallback) {
  const detail = err.response?.data?.detail

  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ')
  }

  if (typeof detail === 'string') {
    return detail
  }

  return fallback
}

function validateForm(formData) {
  const requiredFields = [
    ['workspace_dir', 'Workspace directory'],
    ['logs_dir', 'Logs directory'],
    ['default_branch', 'Default branch'],
    ['default_deploy_path', 'Default deploy path'],
    ['default_service_name', 'Default service name'],
  ]

  for (const [field, label] of requiredFields) {
    if (!String(formData[field]).trim()) {
      return `${label} is required`
    }
  }

  if (!formData.default_deploy_path.trim().startsWith('/')) {
    return 'Default deploy path must start with /'
  }

  for (const field of timeoutFields) {
    const value = Number(formData[field])
    if (!Number.isInteger(value) || value < 30 || value > 3600) {
      return 'Timeout must be an integer from 30 to 3600 seconds'
    }
  }

  return ''
}

function buildPayload(formData) {
  const payload = {
    workspace_dir: formData.workspace_dir.trim(),
    logs_dir: formData.logs_dir.trim(),
    default_branch: formData.default_branch.trim(),
    default_deploy_path: formData.default_deploy_path.trim(),
    default_service_name: formData.default_service_name.trim(),
    build_timeout_seconds: Number(formData.build_timeout_seconds),
    deploy_timeout_seconds: Number(formData.deploy_timeout_seconds),
    auto_deploy_enabled: Boolean(formData.auto_deploy_enabled),
    docker_enabled: Boolean(formData.docker_enabled),
  }

  const webhookSecret = formData.webhook_secret.trim()
  if (webhookSecret) {
    payload.webhook_secret = webhookSecret
  }

  return payload
}

function Section({ title, children }) {
  return (
    <section style={styles.section}>
      <h2 style={styles.sectionTitle}>{title}</h2>
      <div style={styles.grid}>{children}</div>
    </section>
  )
}

function Settings() {
  const [formData, setFormData] = useState(INITIAL_FORM)
  const [savedData, setSavedData] = useState(INITIAL_FORM)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const hasChanges = useMemo(() => JSON.stringify(formData) !== JSON.stringify(savedData), [formData, savedData])

  const loadSettings = async () => {
    setLoading(true)
    setError('')

    try {
      const settings = normalizeSettings(await settingsService.getSettings())
      setFormData(settings)
      setSavedData(settings)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load settings'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target

    setSuccess('')
    setFormData((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccess('')

    const validationError = validateForm(formData)
    if (validationError) {
      setError(validationError)
      return
    }

    setSaving(true)
    try {
      const settings = normalizeSettings(await settingsService.updateSettings(buildPayload(formData)))
      setFormData(settings)
      setSavedData(settings)
      setSuccess('Settings saved')
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save settings'))
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    const confirmed = window.confirm('Reset settings to default values?')
    if (!confirmed) {
      return
    }

    setResetting(true)
    setError('')
    setSuccess('')

    try {
      const settings = normalizeSettings(await settingsService.resetSettings())
      setFormData(settings)
      setSavedData(settings)
      setSuccess('Settings restored to defaults')
    } catch (err) {
      setError(getErrorMessage(err, 'Could not reset settings'))
    } finally {
      setResetting(false)
    }
  }

  if (loading) {
    return (
      <section style={styles.page}>
        <p style={styles.muted}>Loading settings...</p>
      </section>
    )
  }

  return (
    <section style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Settings</h1>
          {hasChanges ? <p style={styles.warningText}>Unsaved changes</p> : <p style={styles.subtitle}>Saved</p>}
        </div>
        <button type="button" onClick={handleReset} disabled={resetting || saving} style={styles.secondaryButton}>
          {resetting ? 'Resetting...' : 'Reset'}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}
      {success && <div style={styles.success}>{success}</div>}

      <form onSubmit={handleSubmit} style={styles.form}>
        <Section title="General">
          <label style={styles.field}>
            <span style={styles.label}>Workspace directory</span>
            <input
              name="workspace_dir"
              value={formData.workspace_dir}
              onChange={handleChange}
              required
              style={styles.input}
            />
          </label>

          <label style={styles.field}>
            <span style={styles.label}>Logs directory</span>
            <input name="logs_dir" value={formData.logs_dir} onChange={handleChange} required style={styles.input} />
          </label>

          <label style={styles.field}>
            <span style={styles.label}>Default branch</span>
            <input
              name="default_branch"
              value={formData.default_branch}
              onChange={handleChange}
              required
              style={styles.input}
            />
          </label>
        </Section>

        <Section title="Build">
          <label style={styles.field}>
            <span style={styles.label}>Build timeout seconds</span>
            <input
              name="build_timeout_seconds"
              value={formData.build_timeout_seconds}
              onChange={handleChange}
              min="30"
              max="3600"
              type="number"
              required
              style={styles.input}
            />
          </label>

          <label style={styles.toggle}>
            <input
              name="auto_deploy_enabled"
              checked={formData.auto_deploy_enabled}
              onChange={handleChange}
              type="checkbox"
            />
            <span>Auto deploy after successful build</span>
          </label>
        </Section>

        <Section title="Deploy">
          <label style={styles.field}>
            <span style={styles.label}>Default deploy path</span>
            <input
              name="default_deploy_path"
              value={formData.default_deploy_path}
              onChange={handleChange}
              required
              style={styles.input}
            />
          </label>

          <label style={styles.field}>
            <span style={styles.label}>Default service name</span>
            <input
              name="default_service_name"
              value={formData.default_service_name}
              onChange={handleChange}
              required
              style={styles.input}
            />
          </label>

          <label style={styles.field}>
            <span style={styles.label}>Deploy timeout seconds</span>
            <input
              name="deploy_timeout_seconds"
              value={formData.deploy_timeout_seconds}
              onChange={handleChange}
              min="30"
              max="3600"
              type="number"
              required
              style={styles.input}
            />
          </label>

          <label style={styles.toggle}>
            <input name="docker_enabled" checked={formData.docker_enabled} onChange={handleChange} type="checkbox" />
            <span>Enable Docker deploy mode</span>
          </label>
        </Section>

        <Section title="Webhook">
          <div style={styles.secretStatus}>
            <span style={styles.label}>Secret status</span>
            <strong style={formData.webhook_secret_configured ? styles.configured : styles.notConfigured}>
              {formData.webhook_secret_configured ? 'Configured' : 'Not configured'}
            </strong>
          </div>

          <label style={styles.field}>
            <span style={styles.label}>New webhook secret</span>
            <input
              name="webhook_secret"
              value={formData.webhook_secret}
              onChange={handleChange}
              type="password"
              autoComplete="new-password"
              placeholder="Leave blank to keep current secret"
              style={styles.input}
            />
          </label>
        </Section>

        <div style={styles.footer}>
          <button type="submit" disabled={saving || resetting || !hasChanges} style={styles.primaryButton}>
            {saving ? 'Saving...' : 'Save settings'}
          </button>
        </div>
      </form>
    </section>
  )
}

const styles = {
  page: {
    maxWidth: '1040px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '16px',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '30px',
    lineHeight: 1.2,
  },
  subtitle: {
    margin: '8px 0 0',
    color: '#166534',
    fontSize: '14px',
    fontWeight: 700,
  },
  warningText: {
    margin: '8px 0 0',
    color: '#92400e',
    fontSize: '14px',
    fontWeight: 700,
  },
  form: {
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '24px',
  },
  section: {
    padding: '0 0 22px',
    marginBottom: '22px',
    borderBottom: '1px solid #e5e7eb',
  },
  sectionTitle: {
    margin: '0 0 14px',
    color: '#111827',
    fontSize: '18px',
    lineHeight: 1.3,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '18px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  label: {
    color: '#374151',
    fontSize: '13px',
    fontWeight: 700,
  },
  input: {
    width: '100%',
    minHeight: '42px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    padding: '10px 12px',
    color: '#111827',
    backgroundColor: '#ffffff',
    outlineColor: '#2563eb',
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    minHeight: '42px',
    color: '#374151',
    fontSize: '14px',
    fontWeight: 600,
  },
  secretStatus: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    gap: '8px',
    minHeight: '42px',
  },
  configured: {
    color: '#166534',
    fontSize: '14px',
  },
  notConfigured: {
    color: '#6b7280',
    fontSize: '14px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'flex-end',
    marginTop: '24px',
  },
  primaryButton: {
    minHeight: '42px',
    border: 0,
    borderRadius: '6px',
    padding: '0 18px',
    color: '#ffffff',
    backgroundColor: '#2563eb',
    fontWeight: 700,
  },
  secondaryButton: {
    minHeight: '38px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    padding: '0 14px',
    color: '#374151',
    backgroundColor: '#ffffff',
    fontWeight: 700,
  },
  error: {
    marginBottom: '16px',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    padding: '12px',
    color: '#991b1b',
    backgroundColor: '#fef2f2',
  },
  success: {
    marginBottom: '16px',
    border: '1px solid #bbf7d0',
    borderRadius: '6px',
    padding: '12px',
    color: '#166534',
    backgroundColor: '#f0fdf4',
  },
  muted: {
    color: '#6b7280',
  },
}

export default Settings
