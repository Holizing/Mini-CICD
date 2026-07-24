import { Route, Routes } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout'
import Build from '../modules/build/pages/Build'
import Deploy from '../modules/deploy/pages/Deploy'
import Projects from '../modules/project/pages/Projects'
import Settings from '../modules/settings/pages/Settings'
import Dashboard from '../shared/pages/Dashboard'
import History from '../shared/pages/History'


function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="build" element={<Build />} />
        <Route path="deploy" element={<Deploy />} />
        <Route path="history" element={<History />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default AppRouter
