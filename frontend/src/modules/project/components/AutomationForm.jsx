import { useEffect, useMemo, useState } from 'react'

import { projectService } from '../services/projectService'


const EMPTY_CONFIG = {
  enabled: false,
  build_type: 'source',
  build_script: '',
  docker_mode: 'build_from_git',
  image_name: '',
  image_tag: 'latest',
  dockerfile_path: './Dockerfile',
  build_context: '.',
  container_name: '',
  port_mapping: '',
  health_check_port: '',
  health_check_path: '/',
}

function normalizeConfig(config) {
  return {
    enabled: Boolean(config.enabled),
    build_type: config.build_type || 'source',
    build_script: config.build_script || '',
    docker_mode: 'build_from_git',
    image_name: config.image_name || '',
    image_tag: config.image_tag || 'latest',
    dockerfile_path: config.dockerfile_path || './Dockerfile',
    build_context: config.build_context || '.',
    container_name: config.container_name || '',
    port_mapping: config.port_mapping || '',
    health_check_port: config.health_check_port || '',
    health_check_path: config.health_check_path || '/',
  }
}

function apiError(error, fallback) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ')
  }
  return typeof detail === 'string' ? detail : fallback
}

function buildPayload(form) {
  const payload = {
    enabled: Boolean(form.enabled),
    build_type: form.build_type,
    build_script: form.build_script.trim() || null,
    health_check_port: form.health_check_port ? Number(form.health_check_port) : null,
    health_check_path: form.health_check_path.trim() || '/',
  }

  if (form.build_type === 'docker') {
    Object.assign(payload, {
      docker_mode: 'build_from_git',
      image_name: form.image_name.trim(),
      image_tag: form.image_tag.trim() || 'latest',
      dockerfile_path: form.dockerfile_path.trim() || './Dockerfile',
      build_context: form.build_context.trim() || '.',
      container_name: form.container_name.trim(),
      port_mapping: form.port_mapping.trim() || null,
    })
  }
  return payload
}

function validate(form) {
  if (!form.health_check_path.trim().startsWith('/')) {
    return 'Health check path must start with /'
  }
  if (form.build_type === 'docker') {
    if (!form.image_name.trim()) return 'Image name is required'
    if (!form.container_name.trim()) return 'Container name is required'
  }
  return ''
}

function AutomationForm({ project, onClose }) {
  const [form, setForm] = useState(EMPTY_CONFIG)
  const [savedForm, setSavedForm] = useState(EMPTY_CONFIG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const changed = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(savedForm),
    [form, savedForm],
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    setMessage('')

    projectService.getAutomation(project.id)
      .then((response) => {
        if (!active) return
        const normalized = normalizeConfig(response)
        setForm(normalized)
        setSavedForm(normalized)
      })
      .catch((requestError) => {
        if (active) setError(apiError(requestError, 'Could not load automation config'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [project.id])

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target
    setMessage('')
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const setBuildType = (buildType) => {
    setMessage('')
    setForm((current) => ({ ...current, build_type: buildType }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    const validationError = validate(form)
    if (validationError) {
      setError(validationError)
      return
    }

    setSaving(true)
    try {
      const response = await projectService.updateAutomation(project.id, buildPayload(form))
      const normalized = normalizeConfig(response)
      setForm(normalized)
      setSavedForm(normalized)
      setMessage('Automation config saved')
    } catch (requestError) {
      setError(apiError(requestError, 'Could not save automation config'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section style={styles.panel}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>Automation: {project.name}</h2>
          <p style={styles.meta}>{project.repo_url} | {project.branch}</p>
        </div>
        <button type="button" onClick={onClose} style={styles.secondaryButton}>Close</button>
      </div>

      {loading ? (
        <div style={styles.muted}>Loading automation config...</div>
      ) : (
        <form onSubmit={handleSubmit}>
          {error && <div style={styles.error}>{error}</div>}
          {message && <div style={styles.success}>{message}</div>}
          {project.status !== 'active' && (
            <div style={styles.warning}>This project is inactive, so webhook pushes will be ignored.</div>
          )}

          <div className="automation-config-grid" style={styles.grid}>
            <label style={styles.toggle}>
              <input
                type="checkbox"
                name="enabled"
                checked={form.enabled}
                onChange={handleChange}
              />
              <span>Enable push automation</span>
            </label>

            <div style={styles.field}>
              <span style={styles.label}>Build type</span>
              <div style={styles.segmented}>
                {['source', 'docker'].map((buildType) => (
                  <button
                    key={buildType}
                    type="button"
                    aria-pressed={form.build_type === buildType}
                    onClick={() => setBuildType(buildType)}
                    style={{
                      ...styles.segment,
                      ...(form.build_type === buildType ? styles.segmentActive : {}),
                    }}
                  >
                    {buildType === 'source' ? 'Source' : 'Docker'}
                  </button>
                ))}
              </div>
            </div>

            <label style={{ ...styles.field, gridColumn: '1 / -1' }}>
              <span style={styles.label}>Build script</span>
              <textarea
                name="build_script"
                value={form.build_script}
                onChange={handleChange}
                rows={4}
                placeholder={'npm ci\nnpm run build'}
                style={{ ...styles.input, resize: 'vertical' }}
              />
            </label>

            {form.build_type === 'docker' && (
              <>
                <label style={styles.field}>
                  <span style={styles.label}>Image name</span>
                  <input name="image_name" value={form.image_name} onChange={handleChange} style={styles.input} />
                </label>
                <label style={styles.field}>
                  <span style={styles.label}>Image tag</span>
                  <input name="image_tag" value={form.image_tag} onChange={handleChange} style={styles.input} />
                </label>
                <label style={styles.field}>
                  <span style={styles.label}>Dockerfile path</span>
                  <input name="dockerfile_path" value={form.dockerfile_path} onChange={handleChange} style={styles.input} />
                </label>
                <label style={styles.field}>
                  <span style={styles.label}>Build context</span>
                  <input name="build_context" value={form.build_context} onChange={handleChange} style={styles.input} />
                </label>
                <label style={styles.field}>
                  <span style={styles.label}>Container name</span>
                  <input name="container_name" value={form.container_name} onChange={handleChange} style={styles.input} />
                </label>
                <label style={styles.field}>
                  <span style={styles.label}>Port mapping</span>
                  <input
                    name="port_mapping"
                    value={form.port_mapping}
                    onChange={handleChange}
                    placeholder="8082:80"
                    style={styles.input}
                  />
                </label>
              </>
            )}

            <label style={styles.field}>
              <span style={styles.label}>Health check port</span>
              <input
                name="health_check_port"
                value={form.health_check_port}
                onChange={handleChange}
                min="1"
                max="65535"
                type="number"
                style={styles.input}
              />
            </label>
            <label style={styles.field}>
              <span style={styles.label}>Health check path</span>
              <input
                name="health_check_path"
                value={form.health_check_path}
                onChange={handleChange}
                style={styles.input}
              />
            </label>
          </div>

          <div style={styles.footer}>
            <span style={styles.changeState}>{changed ? 'Unsaved changes' : 'Saved'}</span>
            <button type="submit" disabled={saving || !changed} style={styles.primaryButton}>
              {saving ? 'Saving...' : 'Save automation'}
            </button>
          </div>
        </form>
      )}
    </section>
  )
}

const styles = {
  panel: {
    marginBottom: '24px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    padding: '22px',
    backgroundColor: '#ffffff',
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
    color: '#111827',
    fontSize: '18px',
  },
  meta: {
    margin: '7px 0 0',
    color: '#6b7280',
    fontSize: '13px',
    overflowWrap: 'anywhere',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '16px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: '7px',
    minWidth: 0,
  },
  label: {
    color: '#374151',
    fontSize: '13px',
    fontWeight: 700,
  },
  input: {
    width: '100%',
    minHeight: '40px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    padding: '9px 11px',
    color: '#111827',
    backgroundColor: '#ffffff',
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    minHeight: '40px',
    color: '#374151',
    fontSize: '14px',
    fontWeight: 700,
  },
  segmented: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    width: '240px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    overflow: 'hidden',
  },
  segment: {
    minHeight: '38px',
    border: 0,
    borderRight: '1px solid #d1d5db',
    color: '#4b5563',
    backgroundColor: '#ffffff',
    fontWeight: 700,
  },
  segmentActive: {
    color: '#ffffff',
    backgroundColor: '#2563eb',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '14px',
    marginTop: '20px',
  },
  changeState: {
    color: '#6b7280',
    fontSize: '13px',
  },
  primaryButton: {
    minHeight: '40px',
    border: 0,
    borderRadius: '6px',
    padding: '0 16px',
    color: '#ffffff',
    backgroundColor: '#2563eb',
    fontWeight: 700,
  },
  secondaryButton: {
    minHeight: '36px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    padding: '0 12px',
    color: '#374151',
    backgroundColor: '#ffffff',
    fontWeight: 700,
  },
  error: {
    marginBottom: '14px',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    padding: '11px',
    color: '#991b1b',
    backgroundColor: '#fef2f2',
  },
  success: {
    marginBottom: '14px',
    border: '1px solid #bbf7d0',
    borderRadius: '6px',
    padding: '11px',
    color: '#166534',
    backgroundColor: '#f0fdf4',
  },
  warning: {
    marginBottom: '14px',
    border: '1px solid #fde68a',
    borderRadius: '6px',
    padding: '11px',
    color: '#92400e',
    backgroundColor: '#fffbeb',
  },
  muted: {
    color: '#6b7280',
  },
}

export default AutomationForm
