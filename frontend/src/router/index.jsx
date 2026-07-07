import { Route, Routes } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout'
import Settings from '../modules/settings/pages/Settings'

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Settings />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default AppRouter
