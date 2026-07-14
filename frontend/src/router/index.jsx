import { Navigate, Route, Routes } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout'
import ProtectedRoute from '../modules/auth/components/ProtectedRoute'
import Login from '../modules/auth/pages/Login'
import Settings from '../modules/settings/pages/Settings'

function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Settings />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRouter
