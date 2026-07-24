import React from 'react'
import ReactDOM from 'react-dom/client'

import './styles.css'


function App() {
  return (
    <main>
      <p className="eyebrow">Mini-CICD verified profile</p>
      <h1>React/Vite deployment is healthy</h1>
      <p>This page was built once and deployed as a static artifact.</p>
    </main>
  )
}


ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
