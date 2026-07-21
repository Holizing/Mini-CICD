import React, { useState, useEffect, useRef } from 'react'

const BuildLog = ({ log, loading }) => {
  const [autoScroll, setAutoScroll] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [currentMatch, setCurrentMatch] = useState(0)
  const logContainerRef = useRef(null)

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [log, autoScroll])

  useEffect(() => {
    if (searchTerm) {
      const lines = log.split('\n')
      const matches = lines
        .map((line, index) => ({ line, index }))
        .filter(({ line }) => line.toLowerCase().includes(searchTerm.toLowerCase()))
      setSearchResults(matches)
      setCurrentMatch(0)
    } else {
      setSearchResults([])
      setCurrentMatch(0)
    }
  }, [searchTerm, log])

  const highlightLog = (logText) => {
    if (!logText) return ''

    const lines = logText.split('\n')
    return lines.map((line, index) => {
      let lineStyle = { color: '#d4d4d4' }
      let icon = ''
      let isMatch = false

      if (searchTerm && line.toLowerCase().includes(searchTerm.toLowerCase())) {
        lineStyle = { backgroundColor: '#fef08a', color: '#000' }
        isMatch = true
      }

      if (line.includes('[INFO]') || line.includes('INFO:')) {
        lineStyle = isMatch ? { backgroundColor: '#fef08a', color: '#000' } : { color: '#60a5fa' }
        icon = 'ℹ '
      } else if (line.includes('[SUCCESS]') || line.includes('SUCCESS:') || line.includes('✓')) {
        lineStyle = isMatch ? { backgroundColor: '#fef08a', color: '#000' } : { color: '#34d399' }
        icon = '✓ '
      } else if (line.includes('[WARNING]') || line.includes('WARNING:') || line.includes('⚠')) {
        lineStyle = isMatch ? { backgroundColor: '#fef08a', color: '#000' } : { color: '#fbbf24' }
        icon = '⚠ '
      } else if (line.includes('[ERROR]') || line.includes('ERROR:') || line.includes('✗') || line.includes('Failed')) {
        lineStyle = isMatch ? { backgroundColor: '#fef08a', color: '#000' } : { color: '#f87171' }
        icon = '✗ '
      }

      return (
        <div key={index} style={{ ...lineStyle, lineHeight: '1.5' }}>
          {icon}{line}
        </div>
      )
    })
  }

  const handleNextMatch = () => {
    if (searchResults.length === 0) return
    const nextMatch = (currentMatch + 1) % searchResults.length
    setCurrentMatch(nextMatch)
    scrollToMatch(nextMatch)
  }

  const handlePrevMatch = () => {
    if (searchResults.length === 0) return
    const prevMatch = (currentMatch - 1 + searchResults.length) % searchResults.length
    setCurrentMatch(prevMatch)
    scrollToMatch(prevMatch)
  }

  const scrollToMatch = (matchIndex) => {
    if (logContainerRef.current && searchResults[matchIndex]) {
      const lineIndex = searchResults[matchIndex].index
      const lineElements = logContainerRef.current.children
      if (lineElements[lineIndex]) {
        lineElements[lineIndex].scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }

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

  const downloadLog = () => {
    if (!log) return
    const blob = new Blob([log], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `build_log_${new Date().toISOString().slice(0, 10)}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '8px',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            fontSize: '12px',
            color: '#6b7280',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              style={{ marginRight: '6px' }}
            />
            Auto-scroll
          </label>
          <button
            onClick={downloadLog}
            disabled={!log}
            style={{
              padding: '4px 8px',
              fontSize: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              cursor: log ? 'pointer' : 'not-allowed',
              backgroundColor: 'white'
            }}
          >
            Download
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search logs..."
            style={{
              padding: '4px 8px',
              fontSize: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              width: '150px'
            }}
          />
          {searchResults.length > 0 && (
            <span style={{ fontSize: '12px', color: '#6b7280' }}>
              {currentMatch + 1}/{searchResults.length}
            </span>
          )}
          <button
            onClick={handlePrevMatch}
            disabled={searchResults.length === 0}
            style={{
              padding: '4px 8px',
              fontSize: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              cursor: searchResults.length > 0 ? 'pointer' : 'not-allowed',
              backgroundColor: 'white'
            }}
          >
            ←
          </button>
          <button
            onClick={handleNextMatch}
            disabled={searchResults.length === 0}
            style={{
              padding: '4px 8px',
              fontSize: '12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              cursor: searchResults.length > 0 ? 'pointer' : 'not-allowed',
              backgroundColor: 'white'
            }}
          >
            →
          </button>
        </div>
      </div>
      <div
        ref={logContainerRef}
        style={{
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
        }}
      >
        {highlightLog(log)}
      </div>
    </div>
  )
}

export default BuildLog
