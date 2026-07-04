import React, { useEffect, useState } from 'react'
import { buildService } from '../services/buildService'
import BuildHistoryTable from '../components/BuildHistoryTable'

const History = () => {
  const [builds, setBuilds] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(0)
  const [limit] = useState(20)

  useEffect(() => {
    fetchBuildHistory()
  }, [page])

  const fetchBuildHistory = async () => {
    try {
      setLoading(true)
      const response = await buildService.getBuildHistory({
        limit,
        offset: page * limit
      })
      setBuilds(response.builds || [])
      setTotal(response.total || 0)
      setError(null)
    } catch (err) {
      setError('Failed to fetch build history')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div>
      <h1 style={{
        fontSize: '28px',
        fontWeight: '700',
        color: '#111827',
        marginBottom: '24px'
      }}>
        Build History
      </h1>

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
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
          <>
            <div style={{
              marginBottom: '16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span style={{
                fontSize: '14px',
                color: '#6b7280'
              }}>
                Total: {total} builds
              </span>
              
              {totalPages > 1 && (
                <div style={{
                  display: 'flex',
                  gap: '8px',
                  alignItems: 'center'
                }}>
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: page === 0 ? '#f3f4f6' : '#3b82f6',
                      color: page === 0 ? '#9ca3af' : 'white',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '14px',
                      fontWeight: '500',
                      cursor: page === 0 ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Previous
                  </button>
                  
                  <span style={{
                    fontSize: '14px',
                    color: '#374151'
                  }}>
                    Page {page + 1} of {totalPages}
                  </span>
                  
                  <button
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page === totalPages - 1}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: page === totalPages - 1 ? '#f3f4f6' : '#3b82f6',
                      color: page === totalPages - 1 ? '#9ca3af' : 'white',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '14px',
                      fontWeight: '500',
                      cursor: page === totalPages - 1 ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Next
                  </button>
                </div>
              )}
            </div>

            <BuildHistoryTable builds={builds} />
          </>
        )}
      </div>
    </div>
  )
}

export default History
