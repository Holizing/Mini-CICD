import React from 'react'
import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Sidebar from './Sidebar'

const Layout = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main style={{
          flex: 1,
          padding: '24px',
          backgroundColor: '#f5f5f5',
          overflow: 'auto'
        }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
