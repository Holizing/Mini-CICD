import React from 'react'

const Navbar = () => {
  return (
    <nav style={{
      backgroundColor: '#111827',
      color: 'white',
      padding: '0 24px',
      height: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <span style={{
          fontSize: '24px',
          fontWeight: '700',
          color: '#60a5fa'
        }}>
          CI/CD
        </span>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px'
      }}>
        <button style={{
          backgroundColor: 'transparent',
          color: '#9ca3af',
          border: 'none',
          padding: '8px 12px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontSize: '14px',
          transition: 'all 0.2s'
        }}
        onMouseEnter={(e) => {
          e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'
          e.target.style.color = 'white'
        }}
        onMouseLeave={(e) => {
          e.target.style.backgroundColor = 'transparent'
          e.target.style.color = '#9ca3af'
        }}>
          Settings
        </button>
      </div>
    </nav>
  )
}

export default Navbar
