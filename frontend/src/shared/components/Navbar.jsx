function Navbar() {
  return (
    <header
      style={{
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        color: '#ffffff',
        backgroundColor: '#0f172a',
      }}
    >
      <strong style={{ fontSize: '18px' }}>Mini CI/CD</strong>
      <span style={{ color: '#cbd5e1', fontSize: '13px' }}>Settings</span>
    </header>
  )
}

export default Navbar
