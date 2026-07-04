import React from 'react'

const StatusBadge = ({ status }) => {
  const getStatusStyle = () => {
    switch (status?.toLowerCase()) {
      case 'running':
        return {
          backgroundColor: '#fef3c7',
          color: '#92400e',
          border: '1px solid #fcd34d'
        }
      case 'success':
        return {
          backgroundColor: '#d1fae5',
          color: '#065f46',
          border: '1px solid #6ee7b7'
        }
      case 'failed':
        return {
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          border: '1px solid #fca5a5'
        }
      default:
        return {
          backgroundColor: '#f3f4f6',
          color: '#374151',
          border: '1px solid #d1d5db'
        }
    }
  }

  const style = getStatusStyle()

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '9999px',
        fontSize: '12px',
        fontWeight: '600',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        ...style
      }}
    >
      {status || 'Unknown'}
    </span>
  )
}

export default StatusBadge
