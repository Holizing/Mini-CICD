import React from 'react'

const StatusBadge = ({ status }) => {
  const getStatusStyle = (status) => {
    switch (status?.toLowerCase()) {
      case 'success':
        return {
          backgroundColor: '#d1fae5',
          color: '#065f46',
          border: '1px solid #10b981'
        }
      case 'failed':
        return {
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          border: '1px solid #ef4444'
        }
      case 'running':
        return {
          backgroundColor: '#dbeafe',
          color: '#1e40af',
          border: '1px solid #3b82f6'
        }
      default:
        return {
          backgroundColor: '#f3f4f6',
          color: '#374151',
          border: '1px solid #d1d5db'
        }
    }
  }

  const style = getStatusStyle(status)

  return (
    <span style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '9999px',
      fontSize: '12px',
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      ...style
    }}>
      {status || 'Unknown'}
    </span>
  )
}

export default StatusBadge
