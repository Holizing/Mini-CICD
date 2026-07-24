import { Navigate, Route, Routes } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout'
import ProtectedRoute from '../modules/auth/components/ProtectedRoute'
import Login from '../modules/auth/pages/Login'
import Build from '../modules/build/pages/Build'
import Deploy from '../modules/deploy/pages/Deploy'
import Projects from '../modules/project/pages/Projects'
import Settings from '../modules/settings/pages/Settings'
import Dashboard from '../shared/pages/Dashboard'
import History from '../shared/pages/History'


function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="build" element={<Build />} />
          <Route path="deploy" element={<Deploy />} />
          <Route path="history" element={<History />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRouter
