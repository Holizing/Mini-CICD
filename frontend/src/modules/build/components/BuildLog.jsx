import React from 'react'

const BuildLog = ({ log, loading }) => {
  if (loading) {
    return (
      <div style={{
        backgroundColor: '#1e1e1e',
        color: '#d4d4d4',
        padding: '16px',
        borderRadius: '8px',
        fontFamily: 'Courier New, monospace',
        fontSize: '13px',
        minHeight: '200px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        Loading logs...
      </div>
    )
  }

  if (!log) {
    return (
      <div style={{
        backgroundColor: '#1e1e1e',
        color: '#d4d4d4',
        padding: '16px',
        borderRadius: '8px',
        fontFamily: 'Courier New, monospace',
        fontSize: '13px',
        minHeight: '200px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        No logs available
      </div>
    )
  }

  return (
    <div style={{
      backgroundColor: '#1e1e1e',
      color: '#d4d4d4',
      padding: '16px',
      borderRadius: '8px',
      fontFamily: 'Courier New, monospace',
      fontSize: '13px',
      minHeight: '200px',
      maxHeight: '500px',
      overflow: 'auto',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word'
    }}>
      {log}
    </div>
  )
}

export default BuildLog
