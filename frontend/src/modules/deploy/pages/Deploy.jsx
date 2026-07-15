import React, { useState, useEffect } from 'react'
import { deployService } from '../services/deployService'
import { buildService } from '../../build/services/buildService'
import StatusBadge from '../../../shared/components/StatusBadge'
import DeployLog from '../components/DeployLog'

const Deploy = () => {
  const [buildId, setBuildId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [projectName, setProjectName] = useState('')
  const [branch, setBranch] = useState('main')
  const [serverIp, setServerIp] = useState('')
  const [serverUser, setServerUser] = useState('root')
  const [serverPassword, setServerPassword] = useState('')
  const [serverSshKey, setServerSshKey] = useState('')
  const [authType, setAuthType] = useState('password') // 'password' or 'ssh_key'
  const [deployPath, setDeployPath] = useState('')
  const [serviceName, setServiceName] = useState('')
  const [deployType, setDeployType] = useState('source')
  const [deployScript, setDeployScript] = useState('')
  // Docker-specific fields
  const [dockerMode, setDockerMode] = useState('build_from_git')
  const [containerName, setContainerName] = useState('')
  const [portMapping, setPortMapping] = useState('')
  const [imageName, setImageName] = useState('')
  const [imageTag, setImageTag] = useState('latest')
  const [dockerImage, setDockerImage] = useState('')
  const [dockerComposeFile, setDockerComposeFile] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentDeploy, setCurrentDeploy] = useState(null)
  const [log, setLog] = useState('')
  const [logLoading, setLogLoading] = useState(false)
  const [error, setError] = useState(null)
  const [builds, setBuilds] = useState([])
  // Stage-related state
  const [stages, setStages] = useState([])
  const [selectedStage, setSelectedStage] = useState(null)
  const [stageLog, setStageLog] = useState('')
  const [viewMode, setViewMode] = useState('timeline') // 'timeline' or 'raw'

  useEffect(() => {
    fetchSuccessfulBuilds()
  }, [])

  // Poll deploy status and log if running
  useEffect(() => {
    let statusIntervalId
    let logIntervalId

    if (currentDeploy && currentDeploy.status === 'running') {
      // Poll status every 2 seconds
      statusIntervalId = setInterval(async () => {
        try {
          const status = await deployService.getDeployStatus(currentDeploy.id)
          setCurrentDeploy(status)

          if (status.status !== 'running') {
            clearInterval(statusIntervalId)
            clearInterval(logIntervalId)
            // Fetch final log
            fetchLog(status.id)
          }
        } catch (err) {
          console.error('Failed to poll deploy status:', err)
        }
      }, 2000)

      // Poll log every 3 seconds while running (reduced from 1s to prevent UI jitter)
      logIntervalId = setInterval(async () => {
        try {
          await fetchLog(currentDeploy.id)
        } catch (err) {
          console.error('Failed to poll deploy log:', err)
        }
      }, 3000)
    }

    return () => {
      if (statusIntervalId) clearInterval(statusIntervalId)
      if (logIntervalId) clearInterval(logIntervalId)
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

    if (!buildId || !projectId || !projectName || !serverIp) {
      setError('Please fill in all required fields')
      return
    }

    if (deployType === 'source' && (!deployPath || !serviceName)) {
      setError('Deploy Path and Service Name are required for source deploy')
      return
    }

    if (deployType === 'docker' && !containerName) {
      setError('Container Name is required for Docker deploy')
      return
    }

    if (deployType === 'docker' && dockerMode === 'existing_image' && !dockerImage) {
      setError('Docker Image is required for Existing Image mode')
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
        branch: deployType === 'docker' && dockerMode === 'existing_image' ? undefined : branch,
        server_ip: serverIp,
        server_user: serverUser,
        server_password: authType === 'password' ? serverPassword || undefined : undefined,
        server_ssh_key: authType === 'ssh_key' ? serverSshKey || undefined : undefined,
        deploy_path: deployType === 'source' ? deployPath : undefined,
        service_name: deployType === 'source' ? serviceName : undefined,
        deploy_type: deployType,
        deploy_script: deployScript || undefined,
        docker_mode: deployType === 'docker' ? dockerMode : undefined,
        container_name: deployType === 'docker' ? containerName : undefined,
        port_mapping: deployType === 'docker' ? portMapping || undefined : undefined,
        image_name: deployType === 'docker' && dockerMode === 'build_from_git' ? imageName : undefined,
        image_tag: deployType === 'docker' && dockerMode === 'build_from_git' ? imageTag : undefined,
        docker_image: deployType === 'docker' && dockerMode === 'existing_image' ? dockerImage : undefined,
        docker_compose_file: deployType === 'docker' && dockerMode === 'existing_image' ? dockerComposeFile : undefined
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
      setDeployType(selectedBuild.build_type || 'source')
      if (selectedBuild.build_type === 'docker') {
        setContainerName(`${selectedBuild.project_name.toLowerCase().replace(/\s+/g, '-')}-container`)
        // Set docker mode from build
        if (selectedBuild.docker_mode) {
          setDockerMode(selectedBuild.docker_mode)
        }
      }
      // Auto-fill Image Name and Tag from build for Docker deploy
      if (selectedBuild.image_name) {
        setImageName(selectedBuild.image_name)
      }
      if (selectedBuild.image_tag) {
        setImageTag(selectedBuild.image_tag)
      }
      // Auto-fill docker_image for existing_image mode
      if (selectedBuild.docker_image) {
        setDockerImage(selectedBuild.docker_image)
      }
      if (selectedBuild.docker_compose_file) {
        setDockerComposeFile(selectedBuild.docker_compose_file)
      }

      // Auto-fill deployment recommendations from detection results (only for successful source builds)
      if (selectedBuild.status === 'success' && selectedBuild.build_type === 'source') {
        if (selectedBuild.recommended_deploy_path) {
          setDeployPath(selectedBuild.recommended_deploy_path)
        }
        if (selectedBuild.recommended_service_name) {
          setServiceName(selectedBuild.recommended_service_name)
        }
        if (selectedBuild.recommended_deploy_script) {
          setDeployScript(selectedBuild.recommended_deploy_script)
        }
      }
    }
  }

  const handleDeployTypeChange = (e) => {
    const newType = e.target.value
    setDeployType(newType)
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

            {deployType !== 'docker' || dockerMode !== 'existing_image' ? (
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
            ) : null}

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
                Authentication Method
              </label>
              <div style={{
                display: 'flex',
                gap: '12px',
                marginBottom: '8px'
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
                    value="password"
                    checked={authType === 'password'}
                    onChange={(e) => setAuthType(e.target.value)}
                    style={{ marginRight: '6px' }}
                  />
                  Password
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
                    value="ssh_key"
                    checked={authType === 'ssh_key'}
                    onChange={(e) => setAuthType(e.target.value)}
                    style={{ marginRight: '6px' }}
                  />
                  SSH Key
                </label>
              </div>

              {authType === 'password' ? (
                <input
                  type="password"
                  value={serverPassword}
                  onChange={(e) => setServerPassword(e.target.value)}
                  placeholder="Enter server password"
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
              ) : (
                <input
                  type="text"
                  value={serverSshKey}
                  onChange={(e) => setServerSshKey(e.target.value)}
                  placeholder="Enter path to SSH private key (e.g., C:/Users/you/.ssh/id_rsa)"
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
              )}
            </div>

            {deployType === 'source' && (
              <>
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
              </>
            )}

            {deployType === 'docker' && (
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
                      Build From Git (Transfer Image)
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
                      Existing Docker Image (Pull from Registry)
                    </label>
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
                    Container Name
                  </label>
                  <input
                    type="text"
                    value={containerName}
                    onChange={(e) => setContainerName(e.target.value)}
                    placeholder="myapp-container"
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
                    Port Mapping
                  </label>
                  <input
                    type="text"
                    value={portMapping}
                    onChange={(e) => setPortMapping(e.target.value)}
                    placeholder="8080:80 (host:container)"
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
                        Image Name
                      </label>
                      <input
                        type="text"
                        value={imageName}
                        readOnly
                        placeholder="Auto-filled from Build"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          backgroundColor: '#f3f4f6',
                          color: '#6b7280'
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
                        readOnly
                        placeholder="Auto-filled from Build"
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          backgroundColor: '#f3f4f6',
                          color: '#6b7280'
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

            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#374151',
                marginBottom: '6px'
              }}>
                Deploy Script (Optional)
                <span style={{
                  fontWeight: '400',
                  color: '#6b7280',
                  fontSize: '12px',
                  marginLeft: '8px'
                }}>
                  Leave empty to use framework's default deployment strategy
                </span>
              </label>
              <textarea
                value={deployScript}
                onChange={(e) => setDeployScript(e.target.value)}
                placeholder={deployType === 'docker' ? 'docker compose -f /opt/app/docker-compose.yml up -d' : 'Leave empty to use automatic framework-based deployment'}
                rows={6}
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
                {deployType === 'docker' ? 'Optional: override default deploy. Image transfer (save/load) is automatic.' : 'Custom deployment commands. Artifact upload and service restart are automatic.'}
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
