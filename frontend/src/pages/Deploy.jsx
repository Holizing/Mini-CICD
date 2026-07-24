import React, { useState, useEffect } from 'react'
import { deployService } from '../services/deployService'
import { buildService } from '../services/buildService'
import StatusBadge from '../components/StatusBadge'
import DeployLog from '../components/DeployLog'

const Deploy = () => {
  const [buildId, setBuildId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [projectName, setProjectName] = useState('')
  const [branch, setBranch] = useState('main')
  const [serverIp, setServerIp] = useState('')
  const [serverUser, setServerUser] = useState('root')
  const [serverPassword, setServerPassword] = useState('')
  const [deployPath, setDeployPath] = useState('')
  const [serviceName, setServiceName] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentDeploy, setCurrentDeploy] = useState(null)
  const [log, setLog] = useState('')
  const [logLoading, setLogLoading] = useState(false)
  const [error, setError] = useState(null)
  const [builds, setBuilds] = useState([])

  useEffect(() => {
    fetchSuccessfulBuilds()
  }, [])

  // Poll deploy status if running
  useEffect(() => {
    let intervalId
    if (currentDeploy && currentDeploy.status === 'running') {
      intervalId = setInterval(async () => {
        try {
          const status = await deployService.getDeployStatus(currentDeploy.id)
          setCurrentDeploy(status)
          
          if (status.status !== 'running') {
            clearInterval(intervalId)
            // Fetch final log
            fetchLog(status.id)
          }
        } catch (err) {
          console.error('Failed to poll deploy status:', err)
        }
      }, 2000)
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [currentDeploy])

  const fetchSuccessfulBuilds = async () => {
    try {
      const response = await buildService.getBuildHistory({ limit: 50 })
      const successfulBuilds = response.builds.filter(b => b.status === 'success')
      setBuilds(successfulBuilds)
    } catch (err) {
      console.error('Failed to fetch builds:', err)
    }
  }

  const fetchLog = async (deployId) => {
    try {
      setLogLoading(true)
      const response = await deployService.getDeployLog(deployId)
      setLog(response.log || '')
    } catch (err) {
      console.error('Failed to fetch log:', err)
    } finally {
      setLogLoading(false)
    }
  }

  const handleStartDeploy = async (e) => {
    e.preventDefault()
    
    if (!buildId || !projectId || !projectName || !branch || !serverIp || !deployPath || !serviceName) {
      setError('Please fill in all required fields')
      return
    }

    try {
      setLoading(true)
      setError(null)
      setCurrentDeploy(null)
      setLog('')

      const response = await deployService.startDeploy({
        build_id: parseInt(buildId),
        project_id: parseInt(projectId),
        project_name: projectName,
        branch,
        server_ip: serverIp,
        server_user: serverUser,
        server_password: serverPassword || undefined,
        deploy_path: deployPath,
        service_name: serviceName
      })

      setCurrentDeploy(response)
      
      // Start fetching logs
      fetchLog(response.id)
    } catch (err) {
      setError('Failed to start deploy: ' + (err.response?.data?.detail || err.message))
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleBuildChange = (e) => {
    const selectedBuildId = e.target.value
    setBuildId(selectedBuildId)
    
    const selectedBuild = builds.find(b => b.id === parseInt(selectedBuildId))
    if (selectedBuild) {
      setProjectId(selectedBuild.project_id)
      setProjectName(selectedBuild.project_name)
      setBranch(selectedBuild.branch)
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
        Deploy
      </h1>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px',
        marginBottom: '24px'
      }}>
        {/* Deploy Form */}
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
            Start New Deploy
          </h2>

          <form onSubmit={handleStartDeploy}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Select Build (Success Only)
              </label>
              <select
                value={buildId}
                onChange={handleBuildChange}
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: 'white'
                }}
              >
                <option value="">Select a successful build</option>
                {builds.map((build) => (
                  <option key={build.id} value={build.id}>
                    #{build.id} - {build.project_name} ({build.branch}) - {new Date(build.start_time).toLocaleString()}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Project ID
              </label>
              <input
                type="number"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="Auto-filled from build"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: '#f9fafb'
                }}
                disabled
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Auto-filled from build"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: '#f9fafb'
                }}
                disabled
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Branch
              </label>
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="Auto-filled from build"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: '#f9fafb'
                }}
                disabled
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Server IP
              </label>
              <input
                type="text"
                value={serverIp}
                onChange={(e) => setServerIp(e.target.value)}
                placeholder="192.168.1.100"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#3b82f6'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#d1d5db'
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Server User
              </label>
              <input
                type="text"
                value={serverUser}
                onChange={(e) => setServerUser(e.target.value)}
                placeholder="root"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#3b82f6'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#d1d5db'
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Server Password (Optional - use SSH key instead)
              </label>
              <input
                type="password"
                value={serverPassword}
                onChange={(e) => setServerPassword(e.target.value)}
                placeholder="Enter password or leave empty for SSH key"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#3b82f6'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#d1d5db'
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Deploy Path
              </label>
              <input
                type="text"
                value={deployPath}
                onChange={(e) => setDeployPath(e.target.value)}
                placeholder="/var/www/myapp"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#3b82f6'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#d1d5db'
                }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Service Name
              </label>
              <input
                type="text"
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                placeholder="myapp"
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#3b82f6'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#d1d5db'
                }}
              />
            </div>

            {error && (
              <div style={{
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                padding: '12px',
                borderRadius: '6px',
                marginBottom: '16px',
                fontSize: '14px'
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: loading ? '#9ca3af' : '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.target.style.backgroundColor = '#059669'
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.target.style.backgroundColor = '#10b981'
                }
              }}
            >
              {loading ? 'Deploying...' : 'Start Deploy'}
            </button>
          </form>
        </div>

        {/* Deploy Status */}
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
            Deploy Status
          </h2>

          {!currentDeploy ? (
            <div style={{
              textAlign: 'center',
              padding: '32px',
              color: '#6b7280'
            }}>
              No deploy running
            </div>
          ) : (
            <div>
              <div style={{
                marginBottom: '16px',
                paddingBottom: '16px',
                borderBottom: '1px solid #e5e7eb'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    Deploy ID:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: '#111827'
                  }}>
                    #{currentDeploy.id}
                  </span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    Build ID:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: '#111827'
                  }}>
                    #{currentDeploy.build_id}
                  </span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    Project:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    fontWeight: '500',
                    color: '#111827'
                  }}>
                    {currentDeploy.project_name}
                  </span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    Branch:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    color: '#111827'
                  }}>
                    {currentDeploy.branch}
                  </span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    Server:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    color: '#111827'
                  }}>
                    {currentDeploy.server_user}@{currentDeploy.server_ip}
                  </span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontSize: '14px',
                    color: '#6b7280'
                  }}>
                    Status:
                  </span>
                  <StatusBadge status={currentDeploy.status} />
                </div>
              </div>

              <button
                onClick={() => fetchLog(currentDeploy.id)}
                disabled={logLoading}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: logLoading ? 'not-allowed' : 'pointer',
                  marginBottom: '16px'
                }}
              >
                {logLoading ? 'Loading...' : 'Refresh Log'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Deploy Log */}
      {currentDeploy && (
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
            Deploy Log
          </h2>
          <DeployLog log={log} loading={logLoading} />
        </div>
      )}
    </div>
  )
}

export default Deploy
