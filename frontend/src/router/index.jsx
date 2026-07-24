import { Routes, Route } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import Dashboard from '../shared/pages/Dashboard'
import Build from '../modules/build/pages/Build'
import Deploy from '../modules/deploy/pages/Deploy'
import History from '../shared/pages/History'

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="build" element={<Build />} />
        <Route path="deploy" element={<Deploy />} />
        <Route path="history" element={<History />} />
      </Route>
    </Routes>
  )
}

export default AppRouter
