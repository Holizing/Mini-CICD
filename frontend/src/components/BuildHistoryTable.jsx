import React from 'react'
import StatusBadge from './StatusBadge'

const BuildHistoryTable = ({ builds }) => {
  if (!builds || builds.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '32px',
        color: '#6b7280'
      }}>
        No build history available
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
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Commit
            </th>
          </tr>
        </thead>
        <tbody>
          {builds.map((build) => (
            <tr
              key={build.id}
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
                #{build.id}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#374151',
                fontWeight: '500'
              }}>
                {build.project_name}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280'
              }}>
                {build.branch}
              </td>
              <td style={{
                padding: '12px 16px'
              }}>
                <StatusBadge status={build.status} />
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280'
              }}>
                {formatDuration(build.duration)}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontSize: '13px'
              }}>
                {formatDate(build.start_time)}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontFamily: 'monospace',
                fontSize: '12px',
                maxWidth: '100px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {build.commit_hash || '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default BuildHistoryTable
