import React from 'react'
import StatusBadge from './StatusBadge'

const DeployHistoryTable = ({ deploys }) => {
  if (!deploys || deploys.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '32px',
        color: '#6b7280'
      }}>
        No deploy history available
      </div>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString()
  }

  const formatDuration = (seconds) => {
    if (!seconds) return '-'
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  return (
    <div style={{
      overflowX: 'auto',
      borderRadius: '8px',
      border: '1px solid #e5e7eb',
      backgroundColor: 'white'
    }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '14px'
      }}>
        <thead>
          <tr style={{
            backgroundColor: '#f9fafb',
            borderBottom: '2px solid #e5e7eb'
          }}>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              ID
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Build ID
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Project
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Branch
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Server
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Status
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Duration
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Start Time
            </th>
          </tr>
        </thead>
        <tbody>
          {deploys.map((deploy) => (
            <tr
              key={deploy.id}
              style={{
                borderBottom: '1px solid #e5e7eb',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f9fafb'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent'
              }}
            >
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontFamily: 'monospace'
              }}>
                #{deploy.id}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontFamily: 'monospace'
              }}>
                #{deploy.build_id}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#374151',
                fontWeight: '500'
              }}>
                {deploy.project_name}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280'
              }}>
                {deploy.branch}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontSize: '13px'
              }}>
                {deploy.server_ip}
              </td>
              <td style={{
                padding: '12px 16px'
              }}>
                <StatusBadge status={deploy.status} />
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280'
              }}>
                {formatDuration(deploy.duration)}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontSize: '13px'
              }}>
                {formatDate(deploy.start_time)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default DeployHistoryTable
