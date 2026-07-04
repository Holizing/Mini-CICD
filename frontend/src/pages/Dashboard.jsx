import React, { useEffect, useState } from 'react'
import { buildService } from '../services/buildService'
import BuildHistoryTable from '../components/BuildHistoryTable'

const Dashboard = () => {
  const [builds, setBuilds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBuildHistory()
  }, [])

  const fetchBuildHistory = async () => {
    try {
      setLoading(true)
      const response = await buildService.getBuildHistory({ limit: 10 })
      setBuilds(response.builds || [])
      setError(null)
    } catch (err) {
      setError('Failed to fetch build history')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{
        fontSize: '28px',
        fontWeight: '700',
        color: '#111827',
        marginBottom: '24px'
      }}>
        Dashboard
      </h1>

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '16px'
        }}>
          Recent Builds
        </h2>

        {loading ? (
          <div style={{
            textAlign: 'center',
            padding: '32px',
            color: '#6b7280'
          }}>
            Loading...
          </div>
        ) : error ? (
          <div style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '16px',
            borderRadius: '8px',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        ) : (
          <BuildHistoryTable builds={builds} />
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '24px'
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <h3 style={{
            fontSize: '14px',
            fontWeight: '600',
            color: '#6b7280',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            Total Builds
          </h3>
          <p style={{
            fontSize: '36px',
            fontWeight: '700',
            color: '#111827'
          }}>
            {builds.length}
          </p>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <h3 style={{
            fontSize: '14px',
            fontWeight: '600',
            color: '#6b7280',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            Successful Builds
          </h3>
          <p style={{
            fontSize: '36px',
            fontWeight: '700',
            color: '#059669'
          }}>
            {builds.filter(b => b.status === 'success').length}
          </p>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <h3 style={{
            fontSize: '14px',
            fontWeight: '600',
            color: '#6b7280',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            Failed Builds
          </h3>
          <p style={{
            fontSize: '36px',
            fontWeight: '700',
            color: '#dc2626'
          }}>
            {builds.filter(b => b.status === 'failed').length}
          </p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
