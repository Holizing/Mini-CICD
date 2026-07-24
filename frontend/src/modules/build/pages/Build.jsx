import React, { useState, useEffect } from 'react'
import { buildService } from '../services/buildService'
import StatusBadge from '../../../shared/components/StatusBadge'
import BuildLog from '../components/BuildLog'

const Build = () => {
  const [projectId, setProjectId] = useState('')
  const [projectName, setProjectName] = useState('')
  const [branch, setBranch] = useState('main')
  const [gitUrl, setGitUrl] = useState('')
  const [buildType, setBuildType] = useState('source')
  const [buildScript, setBuildScript] = useState('')
  // Docker-specific build fields
  const [dockerMode, setDockerMode] = useState('build_from_git')
  const [imageName, setImageName] = useState('')
  const [imageTag, setImageTag] = useState('latest')
  const [dockerfilePath, setDockerfilePath] = useState('./Dockerfile')
  const [buildContext, setBuildContext] = useState('.')
  const [dockerImage, setDockerImage] = useState('')
  const [dockerComposeFile, setDockerComposeFile] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentBuild, setCurrentBuild] = useState(null)
  const [log, setLog] = useState('')
  const [logLoading, setLogLoading] = useState(false)
  const [error, setError] = useState(null)
  // Stage-related state
  const [stages, setStages] = useState([])
  const [selectedStage, setSelectedStage] = useState(null)
  const [stageLog, setStageLog] = useState('')
  const [viewMode, setViewMode] = useState('timeline') // 'timeline' or 'raw'

  useEffect(() => {
    // Poll build status if running
    let intervalId
    if (currentBuild && currentBuild.status === 'running') {
      intervalId = setInterval(async () => {
        try {
          const status = await buildService.getBuildStatus(currentBuild.id)
          setCurrentBuild(status)
          
          // Also fetch stages
          await fetchStages(currentBuild.id)
          
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

  const fetchStages = async (buildId) => {
    try {
      const stagesData = await buildService.getBuildStages(buildId)
      setStages(stagesData || [])
    } catch (err) {
      console.error('Failed to fetch stages:', err)
    }
  }

  const fetchStageLog = async (buildId, stageName) => {
    try {
      const response = await buildService.getStageLog(buildId, stageName)
      setStageLog(response.log || '')
    } catch (err) {
      console.error('Failed to fetch stage log:', err)
    }
  }

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

    if (!projectId || !projectName) {
      setError('Please fill in all required fields')
      return
    }

    if (buildType === 'docker' && dockerMode === 'build_from_git') {
      if (!branch || !gitUrl) {
        setError('Branch and Git URL are required for Build From Git mode')
        return
      }
      if (!imageName) {
        setError('Image Name is required for Docker build')
        return
      }
    }

    if (buildType === 'docker' && dockerMode === 'existing_image') {
      if (!dockerImage) {
        setError('Docker Image is required for Existing Image mode')
        return
      }
    }

    if (buildType === 'source' && (!branch || !gitUrl)) {
      setError('Branch and Git URL are required for Source Deploy')
      return
    }

    try {
      setLoading(true)
      setError(null)
      setCurrentBuild(null)
      setLog('')
      setStages([])
      setSelectedStage(null)
      setStageLog('')
      setViewMode('timeline')

      const response = await buildService.startBuild({
        project_id: parseInt(projectId),
        project_name: projectName,
        branch: buildType === 'docker' && dockerMode === 'existing_image' ? undefined : branch,
        git_url: buildType === 'docker' && dockerMode === 'existing_image' ? undefined : gitUrl,
        build_type: buildType,
        build_script: buildScript || undefined,
        docker_mode: buildType === 'docker' ? dockerMode : undefined,
        image_name: buildType === 'docker' && dockerMode === 'build_from_git' ? imageName : undefined,
        image_tag: buildType === 'docker' && dockerMode === 'build_from_git' ? imageTag : undefined,
        dockerfile_path: buildType === 'docker' && dockerMode === 'build_from_git' ? dockerfilePath : undefined,
        build_context: buildType === 'docker' && dockerMode === 'build_from_git' ? buildContext : undefined,
        docker_image: buildType === 'docker' && dockerMode === 'existing_image' ? dockerImage : undefined,
        docker_compose_file: buildType === 'docker' && dockerMode === 'existing_image' ? dockerComposeFile : undefined
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

  const handleBuildTypeChange = (e) => {
    const newType = e.target.value
    setBuildType(newType)
    // Removed auto-fill - user configures their own script
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

            {buildType !== 'docker' || dockerMode !== 'existing_image' ? (
              <>
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
              </>
            ) : null}

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Build Type
              </label>
              <select
                value={buildType}
                onChange={handleBuildTypeChange}
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

            {buildType === 'docker' && (
              <>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    color: '#374151',
                    marginBottom: '6px'
                  }}>
                    Docker Mode
                  </label>
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}>
                    <label style={{
                      display: 'flex',
                      alignItems: 'center',
                      fontSize: '14px',
                      color: '#374151',
                      cursor: 'pointer'
                    }}>
                      <input
                        type="radio"
                        name="dockerMode"
                        value="build_from_git"
                        checked={dockerMode === 'build_from_git'}
                        onChange={(e) => setDockerMode(e.target.value)}
                        style={{ marginRight: '8px' }}
                      />
                      Build From Git Repository
                    </label>
                    <label style={{
                      display: 'flex',
                      alignItems: 'center',
                      fontSize: '14px',
                      color: '#374151',
                      cursor: 'pointer'
                    }}>
                      <input
                        type="radio"
                        name="dockerMode"
                        value="existing_image"
                        checked={dockerMode === 'existing_image'}
                        onChange={(e) => setDockerMode(e.target.value)}
                        style={{ marginRight: '8px' }}
                      />
                      Existing Docker Image
                    </label>
                  </div>
                </div>

                {dockerMode === 'build_from_git' && (
                  <>
                    <div style={{ marginBottom: '16px' }}>
                      <label style={{
                        display: 'block',
                        fontSize: '14px',
                        fontWeight: '500',
                        color: '#374151',
                        marginBottom: '6px'
                      }}>
                        Image Name <span style={{color: '#dc2626'}}>*</span>
                      </label>
                      <input
                        type="text"
                        value={imageName}
                        onChange={(e) => setImageName(e.target.value)}
                        placeholder="company/backend"
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
                        Image Tag
                      </label>
                      <input
                        type="text"
                        value={imageTag}
                        onChange={(e) => setImageTag(e.target.value)}
                        placeholder="latest"
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
                        Dockerfile Path
                      </label>
                      <input
                        type="text"
                        value={dockerfilePath}
                        onChange={(e) => setDockerfilePath(e.target.value)}
                        placeholder="./Dockerfile"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          fontFamily: 'monospace'
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
                        Build Context
                      </label>
                      <input
                        type="text"
                        value={buildContext}
                        onChange={(e) => setBuildContext(e.target.value)}
                        placeholder="."
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          fontFamily: 'monospace'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#3b82f6'
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#d1d5db'
                        }}
                      />
                    </div>
                  </>
                )}

                {dockerMode === 'existing_image' && (
                  <>
                    <div style={{ marginBottom: '16px' }}>
                      <label style={{
                        display: 'block',
                        fontSize: '14px',
                        fontWeight: '500',
                        color: '#374151',
                        marginBottom: '6px'
                      }}>
                        Docker Image <span style={{color: '#dc2626'}}>*</span>
                      </label>
                      <input
                        type="text"
                        value={dockerImage}
                        onChange={(e) => setDockerImage(e.target.value)}
                        placeholder="nginx:latest"
                        required
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          fontFamily: 'monospace'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#3b82f6'
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#d1d5db'
                        }}
                      />
                      <div style={{
                        fontSize: '12px',
                        color: '#6b7280',
                        marginTop: '4px'
                      }}>
                        Full image name with tag (e.g., nginx:latest, redis:7, ghcr.io/user/project:latest)
                      </div>
                    </div>

                    <div style={{ marginBottom: '16px' }}>
                      <label style={{
                        display: 'block',
                        fontSize: '14px',
                        fontWeight: '500',
                        color: '#374151',
                        marginBottom: '6px'
                      }}>
                        Docker Compose File (Optional)
                      </label>
                      <input
                        type="text"
                        value={dockerComposeFile}
                        onChange={(e) => setDockerComposeFile(e.target.value)}
                        placeholder="docker-compose.yml"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          fontFamily: 'monospace'
                        }}
                        onFocus={(e) => {
                          e.target.style.borderColor = '#3b82f6'
                        }}
                        onBlur={(e) => {
                          e.target.style.borderColor = '#d1d5db'
                        }}
                      />
                      <div style={{
                        fontSize: '12px',
                        color: '#6b7280',
                        marginTop: '4px'
                      }}>
                        Path to Docker Compose file for complex deployments
                      </div>
                    </div>
                  </>
                )}
              </>
            )}

            {!(buildType === 'docker' && dockerMode === 'existing_image') && (
              <div style={{ marginBottom: '16px' }}>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '6px'
                }}>
                  Build Script (Optional)
                </label>
                <textarea
                  value={buildScript}
                  onChange={(e) => setBuildScript(e.target.value)}
                  placeholder={buildType === 'docker' ? 'Leave empty to auto-run: docker build -f ./Dockerfile -t company/backend:latest .' : 'pip install -r requirements.txt\npytest'}
                  rows={8}
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
                  {buildType === 'docker' ? 'Leave empty to auto-run docker build with your Image Name and Tag' : 'Build commands for your language (Python: pip install, NodeJS: npm install, Java: mvn package, Go: go build)'}
                </div>
              </div>
            )}

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

              {/* Build Timeline */}
              {currentBuild && stages.length > 0 && (
                <div style={{
                  marginTop: '20px',
                  padding: '16px',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb'
                }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '12px'
                  }}>
                    <h3 style={{
                      fontSize: '16px',
                      fontWeight: '600',
                      color: '#374151',
                      margin: 0
                    }}>
                      Build Timeline
                    </h3>
                    <div style={{
                      display: 'flex',
                      gap: '8px'
                    }}>
                      <button
                        onClick={() => setViewMode('timeline')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: viewMode === 'timeline' ? '#3b82f6' : '#e5e7eb',
                          color: viewMode === 'timeline' ? 'white' : '#374151',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        Timeline
                      </button>
                      <button
                        onClick={() => setViewMode('raw')}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: viewMode === 'raw' ? '#3b82f6' : '#e5e7eb',
                          color: viewMode === 'raw' ? 'white' : '#374151',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        Raw Log
                      </button>
                    </div>
                  </div>

                  {viewMode === 'timeline' ? (
                    <div>
                      {stages.map((stage, index) => (
                        <div
                          key={stage.id}
                          onClick={() => {
                            setSelectedStage(stage)
                            fetchStageLog(currentBuild.id, stage.stage_name)
                          }}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            padding: '10px',
                            marginBottom: '8px',
                            backgroundColor: selectedStage?.id === stage.id ? '#dbeafe' : 'white',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            border: '1px solid #e5e7eb',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseEnter={(e) => {
                            if (selectedStage?.id !== stage.id) {
                              e.target.style.backgroundColor = '#f3f4f6'
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (selectedStage?.id !== stage.id) {
                              e.target.style.backgroundColor = 'white'
                            }
                          }}
                        >
                          <div style={{
                            marginRight: '12px',
                            fontSize: '16px',
                            color: stage.status === 'success' ? '#10b981' :
                                   stage.status === 'failed' ? '#ef4444' :
                                   stage.status === 'running' ? '#3b82f6' : '#9ca3af'
                          }}>
                            {stage.status === 'success' ? '✔' :
                             stage.status === 'failed' ? '✗' :
                             stage.status === 'running' ? '⏳' : '□'}
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{
                              fontSize: '14px',
                              fontWeight: '500',
                              color: '#111827'
                            }}>
                              {stage.stage_name}
                            </div>
                            {stage.duration && (
                              <div style={{
                                fontSize: '12px',
                                color: '#6b7280',
                                marginTop: '2px'
                              }}>
                                {stage.duration}s
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <BuildLog log={log} loading={logLoading} />
                  )}
                </div>
              )}

              {/* Stage Log Viewer */}
              {selectedStage && viewMode === 'timeline' && (
                <div style={{
                  marginTop: '20px',
                  padding: '16px',
                  backgroundColor: '#f9fafb',
                  borderRadius: '6px',
                  border: '1px solid #e5e7eb'
                }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '12px'
                  }}>
                    <h3 style={{
                      fontSize: '16px',
                      fontWeight: '600',
                      color: '#374151',
                      margin: 0
                    }}>
                      {selectedStage.stage_name} Log
                    </h3>
                    <button
                      onClick={() => setSelectedStage(null)}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#e5e7eb',
                        color: '#374151',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                    >
                      Close
                    </button>
                  </div>
                  <BuildLog log={stageLog} loading={false} />
                </div>
              )}

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
