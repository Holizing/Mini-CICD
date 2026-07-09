import React, { useState, useEffect } from 'react'
import { buildService } from '../services/buildService'
import StatusBadge from '../../../shared/components/StatusBadge'
import BuildLog from '../components/BuildLog'

const Build = () => {
  const [projectId, setProjectId] = useState('')
  const [projectName, setProjectName] = useState('')
  const [branch, setBranch] = useState('main')
  const [gitUrl, setGitUrl] = useState('')
  const [deployType, setDeployType] = useState('source')
  const [buildScript, setBuildScript] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentBuild, setCurrentBuild] = useState(null)
  const [log, setLog] = useState('')
  const [logLoading, setLogLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Poll build status if running
    let intervalId
    if (currentBuild && currentBuild.status === 'running') {
      intervalId = setInterval(async () => {
        try {
          const status = await buildService.getBuildStatus(currentBuild.id)
          setCurrentBuild(status)
          
          if (status.status !== 'running') {
            clearInterval(intervalId)
            // Fetch final log
            fetchLog(status.id)
          }
        } catch (err) {
          console.error('Failed to poll build status:', err)
        }
      }, 2000)
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [currentBuild])

  const fetchLog = async (buildId) => {
    try {
      setLogLoading(true)
      const response = await buildService.getBuildLog(buildId)
      setLog(response.log || '')
    } catch (err) {
      console.error('Failed to fetch log:', err)
    } finally {
      setLogLoading(false)
    }
  }

  const handleStartBuild = async (e) => {
    e.preventDefault()

    if (!projectId || !projectName || !branch || !gitUrl || !buildScript) {
      setError('Please fill in all required fields including Build Script')
      return
    }

    try {
      setLoading(true)
      setError(null)
      setCurrentBuild(null)
      setLog('')

      const response = await buildService.startBuild({
        project_id: parseInt(projectId),
        project_name: projectName,
        branch,
        git_url: gitUrl,
        deploy_type: deployType,
        build_script: buildScript || undefined
      })

      setCurrentBuild(response)

      // Start fetching logs
      fetchLog(response.id)
    } catch (err) {
      setError('Failed to start build: ' + (err.response?.data?.detail || err.message))
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeployTypeChange = (e) => {
    const newType = e.target.value
    setDeployType(newType)

    // Auto-fill build script based on deploy type
    if (newType === 'source') {
      setBuildScript('pip install -r requirements.txt\npytest')
    } else if (newType === 'docker') {
      setBuildScript('docker build -t company/backend:latest .\ndocker push company/backend:latest')
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
        Build
      </h1>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px',
        marginBottom: '24px'
      }}>
        {/* Build Form */}
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
            Start New Build
          </h2>

          <form onSubmit={handleStartBuild}>
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
                placeholder="1"
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
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="my-project"
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
                Branch
              </label>
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="main"
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
                Git URL
              </label>
              <input
                type="text"
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                placeholder="https://github.com/username/repo.git"
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
                Deploy Type
              </label>
              <select
                value={deployType}
                onChange={handleDeployTypeChange}
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
                <option value="source">Source Deploy (Python, NodeJS, Java, etc.)</option>
                <option value="docker">Docker Deploy</option>
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
                Build Script <span style={{color: '#dc2626'}}>*</span>
              </label>
              <textarea
                value={buildScript}
                onChange={(e) => setBuildScript(e.target.value)}
                placeholder={deployType === 'docker' ? 'docker build -t company/backend:latest .\ndocker push company/backend:latest' : 'pip install -r requirements.txt\npytest'}
                rows={8}
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '13px',
                  fontFamily: 'monospace',
                  outline: 'none',
                  transition: 'border-color 0.2s',
                  resize: 'vertical',
                  backgroundColor: '#fafafa'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#3b82f6'
                  e.target.style.backgroundColor = 'white'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#d1d5db'
                  e.target.style.backgroundColor = '#fafafa'
                }}
              />
              <div style={{
                fontSize: '12px',
                color: '#6b7280',
                marginTop: '4px'
              }}>
                {deployType === 'docker' ? 'Docker build and push commands' : 'Build commands for your language (Python: pip install, NodeJS: npm install, Java: mvn package, Go: go build)'}
              </div>
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
                backgroundColor: loading ? '#9ca3af' : '#3b82f6',
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
                  e.target.style.backgroundColor = '#2563eb'
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.target.style.backgroundColor = '#3b82f6'
                }
              }}
            >
              {loading ? 'Building...' : 'Start Build'}
            </button>
          </form>
        </div>

        {/* Build Status */}
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
            Build Status
          </h2>

          {!currentBuild ? (
            <div style={{
              textAlign: 'center',
              padding: '32px',
              color: '#6b7280'
            }}>
              No build running
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
                    Build ID:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: '#111827'
                  }}>
                    #{currentBuild.id}
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
                    {currentBuild.project_name}
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
                    {currentBuild.branch}
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
                    Commit:
                  </span>
                  <span style={{
                    fontSize: '14px',
                    fontFamily: 'monospace',
                    color: '#111827'
                  }}>
                    {currentBuild.commit_hash ? currentBuild.commit_hash.substring(0, 8) : '-'}
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
                  <StatusBadge status={currentBuild.status} />
                </div>

                {currentBuild.duration && (
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span style={{
                      fontSize: '14px',
                      color: '#6b7280'
                    }}>
                      Duration:
                    </span>
                    <span style={{
                      fontSize: '14px',
                      color: '#111827'
                    }}>
                      {currentBuild.duration}s
                    </span>
                  </div>
                )}
              </div>

              <button
                onClick={() => fetchLog(currentBuild.id)}
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

      {/* Build Log */}
      {currentBuild && (
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
            Build Log
          </h2>
          <BuildLog log={log} loading={logLoading} />
        </div>
      )}
    </div>
  )
}

export default Build
