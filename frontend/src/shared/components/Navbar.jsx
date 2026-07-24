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
        <span style={{
          color: '#9ca3af',
          fontSize: '14px'
        }}>
          Mini CI/CD
        </span>
      </div>
    </nav>
  )
}

export default Navbar
