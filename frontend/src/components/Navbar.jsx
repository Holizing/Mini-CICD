import React from 'react'
import { Link } from 'react-router-dom'

const Navbar = () => {
  return (
    <nav style={{
      backgroundColor: '#1f2937',
      color: 'white',
      padding: '0 24px',
      height: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
    }}>
      <Link
        to="/"
        style={{
          color: 'white',
          textDecoration: 'none',
          fontSize: '20px',
          fontWeight: '700',
          letterSpacing: '0.5px'
        }}
      >
        Mini CI/CD
      </Link>
      
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '24px'
      }}>
        <span style={{
          fontSize: '14px',
          color: '#9ca3af'
        }}>
          Welcome, User
        </span>
      </div>
    </nav>
  )
}

export default Navbar
