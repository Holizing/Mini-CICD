import React, { useState, useEffect } from 'react'
import { buildService } from '../../modules/build/services/buildService'
import { deployService } from '../../modules/deploy/services/deployService'
import BuildHistoryTable from '../../modules/build/components/BuildHistoryTable'
import StatusBadge from '../components/StatusBadge'

const Dashboard = () => {
  const [recentBuilds, setRecentBuilds] = useState([])
  const [recentDeploys, setRecentDeploys] = useState([])
  const [stats, setStats] = useState({
    totalBuilds: 0,
    successfulBuilds: 0,
    failedBuilds: 0,
    totalDeploys: 0,
    successfulDeploys: 0,
    failedDeploys: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      
      const [buildsResponse, deploysResponse] = await Promise.all([
        buildService.getBuildHistory({ limit: 10 }),
        deployService.getDeployHistory({ limit: 10 })
      ])

      setRecentBuilds(buildsResponse.builds)
      setRecentDeploys(deploysResponse.deploys)

      // Calculate stats
      const allBuilds = await buildService.getBuildHistory({ limit: 100 })
      const allDeploys = await deployService.getDeployHistory({ limit: 100 })

      setStats({
        totalBuilds: allBuilds.total,
        successfulBuilds: allBuilds.builds.filter(b => b.status === 'success').length,
        failedBuilds: allBuilds.builds.filter(b => b.status === 'failed').length,
        totalDeploys: allDeploys.total,
        successfulDeploys: allDeploys.deploys.filter(d => d.status === 'success').length,
        failedDeploys: allDeploys.deploys.filter(d => d.status === 'failed').length
      })
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '400px',
        color: '#6b7280'
      }}>
        Loading...
      </div>
    )
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

      {/* Stats Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '8px'
          }}>
            Total Builds
          </div>
          <div style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#111827'
          }}>
            {stats.totalBuilds}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '8px'
          }}>
            Successful Builds
          </div>
          <div style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#10b981'
          }}>
            {stats.successfulBuilds}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '8px'
          }}>
            Failed Builds
          </div>
          <div style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#ef4444'
          }}>
            {stats.failedBuilds}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '8px'
          }}>
            Total Deploys
          </div>
          <div style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#111827'
          }}>
            {stats.totalDeploys}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '8px'
          }}>
            Successful Deploys
          </div>
          <div style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#10b981'
          }}>
            {stats.successfulDeploys}
          </div>
        </div>

        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '8px'
          }}>
            Failed Deploys
          </div>
          <div style={{
            fontSize: '32px',
            fontWeight: '700',
            color: '#ef4444'
          }}>
            {stats.failedDeploys}
          </div>
        </div>
      </div>

      {/* Recent Builds */}
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        marginBottom: '24px'
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '16px'
        }}>
          Recent Builds
        </h2>
        <BuildHistoryTable builds={recentBuilds} />
      </div>

      {/* Recent Deploys */}
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '16px'
        }}>
          Recent Deploys
        </h2>
        <DeployHistoryTable deploys={recentDeploys} />
      </div>
    </div>
  )
}

const DeployHistoryTable = ({ deploys }) => {
  if (!deploys || deploys.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '32px',
        color: '#6b7280'
      }}>
        No deploy history available
      </div>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString()
  }

  return (
    <div style={{
      overflowX: 'auto',
      borderRadius: '8px',
      border: '1px solid #e5e7eb',
      backgroundColor: 'white'
    }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '14px'
      }}>
        <thead>
          <tr style={{
            backgroundColor: '#f9fafb',
            borderBottom: '2px solid #e5e7eb'
          }}>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              ID
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Project
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Status
            </th>
            <th style={{
              padding: '12px 16px',
              textAlign: 'left',
              fontWeight: '600',
              color: '#374151',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              Start Time
            </th>
          </tr>
        </thead>
        <tbody>
          {deploys.map((deploy) => (
            <tr
              key={deploy.id}
              style={{
                borderBottom: '1px solid #e5e7eb',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f9fafb'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent'
              }}
            >
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontFamily: 'monospace'
              }}>
                #{deploy.id}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#374151',
                fontWeight: '500'
              }}>
                {deploy.project_name}
              </td>
              <td style={{
                padding: '12px 16px'
              }}>
                <StatusBadge status={deploy.status} />
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#6b7280',
                fontSize: '13px'
              }}>
                {formatDate(deploy.start_time)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default Dashboard
