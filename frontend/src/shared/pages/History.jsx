import React, { useState, useEffect } from 'react'
import { buildService } from '../../modules/build/services/buildService'
import { deployService } from '../../modules/deploy/services/deployService'
import BuildHistoryTable from '../../modules/build/components/BuildHistoryTable'
import DeployHistoryTable from '../../modules/deploy/components/DeployHistoryTable'

const History = () => {
  const [activeTab, setActiveTab] = useState('builds')
  const [builds, setBuilds] = useState([])
  const [deploys, setDeploys] = useState([])
  const [buildsTotal, setBuildsTotal] = useState(0)
  const [deploysTotal, setDeploysTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [limit] = useState(20)

  useEffect(() => {
    fetchData()
  }, [activeTab, page])

  const fetchData = async () => {
    try {
      setLoading(true)
      
      if (activeTab === 'builds') {
        const response = await buildService.getBuildHistory({ limit, offset: page * limit })
        setBuilds(response.builds)
        setBuildsTotal(response.total)
      } else {
        const response = await deployService.getDeployHistory({ limit, offset: page * limit })
        setDeploys(response.deploys)
        setDeploysTotal(response.total)
      }
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.ceil((activeTab === 'builds' ? buildsTotal : deploysTotal) / limit)

  return (
    <div>
      <h1 style={{
        fontSize: '28px',
        fontWeight: '700',
        color: '#111827',
        marginBottom: '24px'
      }}>
        History
      </h1>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '4px',
        marginBottom: '24px',
        borderBottom: '2px solid #e5e7eb'
      }}>
        <button
          onClick={() => {
            setActiveTab('builds')
            setPage(0)
          }}
          style={{
            padding: '12px 24px',
            backgroundColor: activeTab === 'builds' ? 'white' : 'transparent',
            color: activeTab === 'builds' ? '#111827' : '#6b7280',
            border: 'none',
            borderBottom: activeTab === 'builds' ? '2px solid #3b82f6' : '2px solid transparent',
            marginBottom: '-2px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
        >
          Builds ({buildsTotal})
        </button>
        <button
          onClick={() => {
            setActiveTab('deploys')
            setPage(0)
          }}
          style={{
            padding: '12px 24px',
            backgroundColor: activeTab === 'deploys' ? 'white' : 'transparent',
            color: activeTab === 'deploys' ? '#111827' : '#6b7280',
            border: 'none',
            borderBottom: activeTab === 'deploys' ? '2px solid #3b82f6' : '2px solid transparent',
            marginBottom: '-2px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
        >
          Deploys ({deploysTotal})
        </button>
      </div>

      {/* Content */}
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        minHeight: '400px'
      }}>
        {loading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '300px',
            color: '#6b7280'
          }}>
            Loading...
          </div>
        ) : activeTab === 'builds' ? (
          <BuildHistoryTable builds={builds} />
        ) : (
          <DeployHistoryTable deploys={deploys} />
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '8px',
          marginTop: '24px'
        }}>
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{
              padding: '8px 16px',
              backgroundColor: page === 0 ? '#f3f4f6' : 'white',
              color: page === 0 ? '#9ca3af' : '#111827',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px',
              cursor: page === 0 ? 'not-allowed' : 'pointer'
            }}
          >
            Previous
          </button>

          <span style={{
            fontSize: '14px',
            color: '#6b7280'
          }}>
            Page {page + 1} of {totalPages}
          </span>

          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={page === totalPages - 1}
            style={{
              padding: '8px 16px',
              backgroundColor: page === totalPages - 1 ? '#f3f4f6' : 'white',
              color: page === totalPages - 1 ? '#9ca3af' : '#111827',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px',
              cursor: page === totalPages - 1 ? 'not-allowed' : 'pointer'
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default History
