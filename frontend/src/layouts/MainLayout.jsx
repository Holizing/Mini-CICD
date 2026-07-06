import { Outlet } from 'react-router-dom'

import Navbar from '../shared/components/Navbar'
import Sidebar from '../shared/components/Sidebar'

const MainLayout = () => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
      backgroundColor: '#f3f4f6',
    }}>
      <Navbar />
      <div style={{ display: 'flex', flex: 1 }}>
        <Sidebar />
        <main style={{ flex: 1, padding: '24px', overflow: 'auto' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default MainLayout
