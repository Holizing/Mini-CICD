import { Outlet } from 'react-router-dom'

import Navbar from '../shared/components/Navbar'
import Sidebar from '../shared/components/Sidebar'

function MainLayout() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6' }}>
      <Navbar />
      <div className="app-shell" style={{ display: 'flex', alignItems: 'stretch' }}>
        <Sidebar />
        <main className="app-shell__content" style={{ flex: 1, minWidth: 0, padding: '28px' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default MainLayout
