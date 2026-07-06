import { Routes, Route } from 'react-router-dom'

import MainLayout from '../layouts/MainLayout'
import Projects from '../modules/project/pages/Projects'

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Projects />} />
        <Route path="projects" element={<Projects />} />
      </Route>
    </Routes>
  )
}

export default AppRouter
