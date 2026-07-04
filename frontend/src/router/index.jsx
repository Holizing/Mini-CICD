import { Routes, Route } from 'react-router-dom'
import Layout from '../components/Layout'
import Dashboard from '../pages/Dashboard'
import Build from '../pages/Build'
import History from '../pages/History'

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="build" element={<Build />} />
        <Route path="history" element={<History />} />
      </Route>
    </Routes>
  )
}

export default AppRouter
