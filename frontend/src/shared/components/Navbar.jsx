const Navbar = () => {
  return (
    <header style={{
      height: '64px',
      backgroundColor: 'white',
      borderBottom: '1px solid #e5e7eb',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
    }}>
      <div style={{
        fontSize: '18px',
        fontWeight: '700',
        color: '#111827',
      }}>
        Mini CI/CD
      </div>
      <div style={{
        fontSize: '14px',
        color: '#6b7280',
      }}>
        Project Management
      </div>
    </header>
  )
}

export default Navbar
