import { useCallback, useEffect, useState } from 'react'

import { automationService } from '../services/automationService'


const ACTIVE_STATUSES = new Set(['queued', 'building', 'deploying'])

const STATUS_STYLES = {
  queued: { backgroundColor: '#f3f4f6', color: '#4b5563' },
  building: { backgroundColor: '#dbeafe', color: '#1d4ed8' },
  build_succeeded: { backgroundColor: '#e0f2fe', color: '#0369a1' },
  deploying: { backgroundColor: '#fef3c7', color: '#92400e' },
  success: { backgroundColor: '#dcfce7', color: '#166534' },
  failed: { backgroundColor: '#fee2e2', color: '#991b1b' },
  ignored: { backgroundColor: '#f3f4f6', color: '#6b7280' },
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function shortValue(value, length = 10) {
  if (!value) return '-'
  return value.length > length ? `${value.slice(0, length)}...` : value
}

function getErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

function Automation() {
  const [deliveries, setDeliveries] = useState([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const loadDeliveries = useCallback(async ({ quiet = false } = {}) => {
    if (quiet) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError('')

    try {
      const response = await automationService.getDeliveries({
        limit: 100,
        ...(statusFilter ? { status: statusFilter } : {}),
      })
      setDeliveries(response.deliveries || [])
      setTotal(response.total || 0)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Could not load webhook deliveries'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [statusFilter])

  useEffect(() => {
    loadDeliveries()
  }, [loadDeliveries])

  useEffect(() => {
    if (!deliveries.some((delivery) => ACTIVE_STATUSES.has(delivery.status))) {
      return undefined
    }
    const timer = window.setInterval(() => loadDeliveries({ quiet: true }), 4000)
    return () => window.clearInterval(timer)
  }, [deliveries, loadDeliveries])

  return (
    <section style={styles.page}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Automation</h1>
          <p style={styles.subtitle}>
            {total} webhook {total === 1 ? 'delivery' : 'deliveries'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadDeliveries({ quiet: true })}
          disabled={loading || refreshing}
          style={styles.secondaryButton}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div style={styles.toolbar}>
        <label style={styles.filterField}>
          <span style={styles.label}>Status</span>
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            style={styles.select}
          >
            <option value="">All statuses</option>
            <option value="queued">Queued</option>
            <option value="building">Building</option>
            <option value="build_succeeded">Build succeeded</option>
            <option value="deploying">Deploying</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="ignored">Ignored</option>
          </select>
        </label>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {loading ? (
        <div style={styles.empty}>Loading deliveries...</div>
      ) : deliveries.length === 0 ? (
        <div style={styles.empty}>No webhook deliveries match this filter.</div>
      ) : (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeaderRow}>
                {['Delivery', 'Repository', 'Branch / Commit', 'Pipeline', 'Status', 'Received', 'Result'].map((label) => (
                  <th key={label} style={styles.tableHeader}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deliveries.map((delivery) => (
                <tr key={delivery.id} style={styles.tableRow}>
                  <td style={styles.cell}>
                    <code title={delivery.delivery_id}>{shortValue(delivery.delivery_id, 12)}</code>
                    <div style={styles.mutedSmall}>{delivery.event_type}</div>
                  </td>
                  <td style={styles.cell}>{delivery.repository || '-'}</td>
                  <td style={styles.cell}>
                    <div>{delivery.branch || '-'}</div>
                    <code title={delivery.commit_sha || ''}>{shortValue(delivery.commit_sha, 8)}</code>
                  </td>
                  <td style={styles.cell}>
                    <div>Build {delivery.build_id ? `#${delivery.build_id}` : '-'}</div>
                    <div>Deploy {delivery.deploy_id ? `#${delivery.deploy_id}` : '-'}</div>
                  </td>
                  <td style={styles.cell}>
                    <span style={{ ...styles.status, ...(STATUS_STYLES[delivery.status] || STATUS_STYLES.queued) }}>
                      {delivery.status.replaceAll('_', ' ')}
                    </span>
                  </td>
                  <td style={styles.cell}>{formatDate(delivery.received_at)}</td>
                  <td style={{ ...styles.cell, ...styles.resultCell }}>
                    {delivery.error_message || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

const styles = {
  page: {
    maxWidth: '1280px',
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
    fontSize: '28px',
    lineHeight: 1.2,
  },
  subtitle: {
    margin: '7px 0 0',
    color: '#6b7280',
    fontSize: '14px',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'end',
    gap: '12px',
    marginBottom: '16px',
  },
  filterField: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    color: '#374151',
    fontSize: '13px',
    fontWeight: 700,
  },
  select: {
    minWidth: '190px',
    minHeight: '40px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    padding: '8px 10px',
    backgroundColor: '#ffffff',
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
  tableWrap: {
    overflowX: 'auto',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    backgroundColor: '#ffffff',
  },
  table: {
    width: '100%',
    minWidth: '1040px',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  tableHeaderRow: {
    borderBottom: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
  },
  tableHeader: {
    padding: '12px 14px',
    color: '#374151',
    textAlign: 'left',
    fontWeight: 700,
  },
  tableRow: {
    borderBottom: '1px solid #e5e7eb',
  },
  cell: {
    padding: '12px 14px',
    color: '#374151',
    verticalAlign: 'top',
    lineHeight: 1.5,
  },
  resultCell: {
    maxWidth: '280px',
    color: '#6b7280',
    overflowWrap: 'anywhere',
  },
  mutedSmall: {
    marginTop: '3px',
    color: '#6b7280',
    fontSize: '12px',
  },
  status: {
    display: 'inline-flex',
    borderRadius: '999px',
    padding: '4px 8px',
    fontSize: '12px',
    fontWeight: 700,
    textTransform: 'capitalize',
    whiteSpace: 'nowrap',
  },
  empty: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '40px 20px',
    color: '#6b7280',
    backgroundColor: '#ffffff',
    textAlign: 'center',
  },
  error: {
    marginBottom: '16px',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    padding: '12px',
    color: '#991b1b',
    backgroundColor: '#fef2f2',
  },
}

export default Automation
