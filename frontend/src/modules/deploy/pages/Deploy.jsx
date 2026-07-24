import React, { useEffect, useRef, useState } from 'react'
import { deployService } from '../services/deployService'
import { buildService } from '../../build/services/buildService'
import { projectService } from '../../project/services/projectService'
import StatusBadge from '../../../shared/components/StatusBadge'
import DeployLog from '../components/DeployLog'

const Deploy = () => {
  const [buildId, setBuildId] = useState('')
  const [selectedProject, setSelectedProject] = useState(null)
  const [projectLoading, setProjectLoading] = useState(false)
  const [projectError, setProjectError] = useState('')
  const [serverIp, setServerIp] = useState('')
  const [serverUser, setServerUser] = useState('root')
  const [serverPassword, setServerPassword] = useState('')
  const [serverSshKey, setServerSshKey] = useState('')
  const [authType, setAuthType] = useState('password') // 'password' or 'ssh_key'
  const [deployPath, setDeployPath] = useState('')
  const [serviceName, setServiceName] = useState('')
  const [deployType, setDeployType] = useState('source')
  const [deployScript, setDeployScript] = useState('')
  const [deployScriptSuggestion, setDeployScriptSuggestion] = useState('')
  // Docker-specific fields
  const [dockerMode, setDockerMode] = useState('build_from_git')
  const [containerName, setContainerName] = useState('')
  const [portMapping, setPortMapping] = useState('')
  const [imageName, setImageName] = useState('')
  const [imageTag, setImageTag] = useState('latest')
  const [dockerImage, setDockerImage] = useState('')
  const [dockerComposeFile, setDockerComposeFile] = useState('')
  const [healthCheckPort, setHealthCheckPort] = useState('')
  const [healthCheckPath, setHealthCheckPath] = useState('/')
  const [loading, setLoading] = useState(false)
  const [currentDeploy, setCurrentDeploy] = useState(null)
  const [log, setLog] = useState('')
  const [logLoading, setLogLoading] = useState(false)
  const [error, setError] = useState(null)
  const [builds, setBuilds] = useState([])
  const [buildsLoading, setBuildsLoading] = useState(true)
  const [buildsError, setBuildsError] = useState('')
  const [capabilities, setCapabilities] = useState([])
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true)
  const [capabilitiesError, setCapabilitiesError] = useState('')
  // Stage-related state
  const [stages, setStages] = useState([])
  const [selectedStage, setSelectedStage] = useState(null)
  const [stageLog, setStageLog] = useState('')
  const [viewMode, setViewMode] = useState('timeline') // 'timeline' or 'raw'
  const projectRequestId = useRef(0)

  const selectedBuild = builds.find((build) => build.id === Number(buildId))
  const selectedCapability = selectedBuild
    ? capabilities
      .filter((capability) => {
        if (selectedBuild.build_type === 'docker') {
          return capability.id === 'docker'
        }
        return (
          capability.frameworks.includes(selectedBuild.detected_framework)
          && capability.runtimes.includes(selectedBuild.detected_runtime)
          && capability.artifact_types.includes(selectedBuild.artifact_type)
        )
      })
      .sort((left, right) => {
        if (left.status === 'verified') return -1
        if (right.status === 'verified') return 1
        return 0
      })[0]
    : null
  const projectReady = (
    selectedBuild
    && selectedProject
    && selectedProject.id === selectedBuild.project_id
    && selectedProject.status === 'active'
  )
  const profileReady = Boolean(selectedCapability?.enabled)
  const startDisabled = (
    loading
    || buildsLoading
    || projectLoading
    || capabilitiesLoading
    || !projectReady
    || !profileReady
  )

  useEffect(() => {
    fetchSuccessfulBuilds()
    fetchCapabilities()
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

          // Also fetch stages
          await fetchStages(currentDeploy.id)

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
      setBuildsLoading(true)
      setBuildsError('')
      const response = await buildService.getBuildHistory({ limit: 50 })
      const successfulBuilds = response.builds.filter(b => b.status === 'success')
      setBuilds(successfulBuilds)
    } catch (err) {
      console.error('Failed to fetch builds:', err)
      setBuildsError(err.response?.data?.detail || 'Failed to load successful builds')
    } finally {
      setBuildsLoading(false)
    }
  }

  const fetchCapabilities = async () => {
    try {
      setCapabilitiesLoading(true)
      setCapabilitiesError('')
      setCapabilities(await deployService.getCapabilities())
    } catch (err) {
      console.error('Failed to load deployment capabilities:', err)
      setCapabilitiesError(
        err.response?.data?.detail || 'Failed to load deployment capabilities'
      )
    } finally {
      setCapabilitiesLoading(false)
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

  const fetchStages = async (deployId) => {
    try {
      const stagesData = await deployService.getDeployStages(deployId)
      setStages(stagesData || [])
    } catch (err) {
      console.error('Failed to fetch stages:', err)
    }
  }

  const fetchStageLog = async (deployId, stageName) => {
    try {
      const response = await deployService.getStageLog(deployId, stageName)
      setStageLog(response.log || '')
    } catch (err) {
      console.error('Failed to fetch stage log:', err)
    }
  }

  const handleStartDeploy = async (e) => {
    e.preventDefault()

    if (!selectedBuild || !projectReady || !profileReady || !serverIp) {
      setError('Please select a build with an active project and fill in all required fields')
      return
    }

    if (authType === 'password' && !serverPassword) {
      setError('Server Password is required')
      return
    }

    if (authType === 'ssh_key' && !serverSshKey) {
      setError('SSH Key path is required')
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

    try {
      setLoading(true)
      setError(null)
      setCurrentDeploy(null)
      setLog('')
      setStages([])
      setSelectedStage(null)
      setStageLog('')
      setViewMode('timeline')

      const response = await deployService.startDeploy({
        build_id: parseInt(buildId),
        server_ip: serverIp,
        server_user: serverUser,
        server_password: authType === 'password' ? serverPassword || undefined : undefined,
        server_ssh_key: authType === 'ssh_key' ? serverSshKey || undefined : undefined,
        deploy_path: deployType === 'source' ? deployPath : undefined,
        service_name: deployType === 'source' ? serviceName : undefined,
        deploy_script: deployScript || undefined,
        container_name: deployType === 'docker' ? containerName : undefined,
        port_mapping: deployType === 'docker' ? portMapping || undefined : undefined,
        health_check_port: healthCheckPort ? parseInt(healthCheckPort) : undefined,
        health_check_path: healthCheckPath || '/'
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

  const handleBuildChange = async (e) => {
    const selectedBuildId = e.target.value
    setBuildId(selectedBuildId)
    setSelectedProject(null)
    setProjectLoading(false)
    setProjectError('')
    setDeployPath('')
    setServiceName('')
    setDeployScript('')
    setDeployScriptSuggestion('')
    setHealthCheckPort('')
    setHealthCheckPath('/')
    const requestId = ++projectRequestId.current

    const selectedBuild = builds.find(b => b.id === parseInt(selectedBuildId))
    if (!selectedBuild) {
      setDeployType('source')
      setDockerMode('build_from_git')
      setContainerName('')
      setImageName('')
      setImageTag('latest')
      setDockerImage('')
      setDockerComposeFile('')
      return
    }

    setDeployType(selectedBuild.build_type || 'source')
    setDockerMode(selectedBuild.docker_mode || 'build_from_git')
    setContainerName(
      selectedBuild.build_type === 'docker'
        ? `${selectedBuild.project_name.toLowerCase().replace(/\s+/g, '-')}-container`
        : ''
    )
    setImageName(selectedBuild.image_name || '')
    setImageTag(selectedBuild.image_tag || 'latest')
    setDockerImage(selectedBuild.docker_image || '')
    setDockerComposeFile(selectedBuild.docker_compose_file || '')
    setDeployScriptSuggestion(selectedBuild.recommended_deploy_script || '')
    const capability = capabilities
      .filter((item) => (
        selectedBuild.build_type === 'docker'
          ? item.id === 'docker'
          : (
            item.frameworks.includes(selectedBuild.detected_framework)
            && item.runtimes.includes(selectedBuild.detected_runtime)
            && item.artifact_types.includes(selectedBuild.artifact_type)
          )
      ))
      .sort((left, right) => {
        if (left.status === 'verified') return -1
        if (right.status === 'verified') return 1
        return 0
      })[0]
    setHealthCheckPort(capability?.default_health_check_port || '')

    try {
      setProjectLoading(true)
      const project = await projectService.getProject(selectedBuild.project_id)
      if (requestId !== projectRequestId.current) {
        return
      }
      if (project.status !== 'active') {
        setProjectError('This build belongs to an inactive project')
        return
      }

      setSelectedProject(project)
      if (selectedBuild.build_type === 'source') {
        setDeployPath(project.deploy_path || selectedBuild.recommended_deploy_path || '')
        setServiceName(project.service_name || selectedBuild.recommended_service_name || '')
      }
    } catch (err) {
      if (requestId === projectRequestId.current) {
        setProjectError(
          err.response?.status === 404
            ? 'Project for this build no longer exists'
            : (err.response?.data?.detail || 'Failed to load the project')
        )
      }
    } finally {
      if (requestId === projectRequestId.current) {
        setProjectLoading(false)
      }
    }
  }

  const handleDeployScriptKeyDown = (e) => {
    // Tab to accept suggestion
    if (e.key === 'Tab' && deployScriptSuggestion && !deployScript) {
      e.preventDefault()
      setDeployScript(deployScriptSuggestion)
      setDeployScriptSuggestion('')
    }
    // Esc to dismiss suggestion
    if (e.key === 'Escape' && deployScriptSuggestion) {
      e.preventDefault()
      setDeployScriptSuggestion('')
    }
  }

  const handleDeployScriptChange = (e) => {
    const newValue = e.target.value
    setDeployScript(newValue)
    // Clear suggestion when user starts typing
    if (newValue && deployScriptSuggestion) {
      setDeployScriptSuggestion('')
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

      <div className="execution-grid" style={{
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
                disabled={buildsLoading}
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: buildsLoading ? '#f3f4f6' : 'white'
                }}
              >
                <option value="">
                  {buildsLoading ? 'Loading builds...' : 'Select a successful build'}
                </option>
                {builds.map((build) => (
                  <option key={build.id} value={build.id}>
                    #{build.id} - {build.project_name} ({build.branch}) - {new Date(build.start_time).toLocaleString()}
                  </option>
                ))}
              </select>
            </div>

            {buildsError && (
              <div style={{
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                padding: '12px',
                borderRadius: '6px',
                marginBottom: '16px',
                fontSize: '14px'
              }}>
                {buildsError}
              </div>
            )}

            {!buildsLoading && !buildsError && builds.length === 0 && (
              <div style={{
                padding: '12px 0',
                marginBottom: '16px',
                color: '#6b7280',
                fontSize: '14px'
              }}>
                No successful builds are available.
              </div>
            )}

            {projectLoading && (
              <div style={{ marginBottom: '16px', color: '#6b7280', fontSize: '14px' }}>
                Loading project...
              </div>
            )}

            {projectError && (
              <div style={{
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                padding: '12px',
                borderRadius: '6px',
                marginBottom: '16px',
                fontSize: '14px'
              }}>
                {projectError}
              </div>
            )}

            {capabilitiesError && (
              <div style={{
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                padding: '12px',
                borderRadius: '6px',
                marginBottom: '16px',
                fontSize: '14px'
              }}>
                {capabilitiesError}
              </div>
            )}

            {selectedBuild && !capabilitiesLoading && !capabilitiesError && (
              <div style={{
                backgroundColor: selectedCapability?.enabled ? '#ecfdf5' : '#fff7ed',
                border: `1px solid ${selectedCapability?.enabled ? '#a7f3d0' : '#fed7aa'}`,
                color: selectedCapability?.enabled ? '#065f46' : '#9a3412',
                padding: '12px',
                borderRadius: '6px',
                marginBottom: '16px',
                fontSize: '14px'
              }}>
                <strong>
                  {selectedCapability?.status === 'verified' && 'Verified'}
                  {selectedCapability?.status === 'experimental_enabled' && 'Experimental enabled'}
                  {selectedCapability?.status === 'experimental_disabled' && 'Experimental disabled'}
                  {!selectedCapability && 'Unsupported'}
                </strong>
                <span>
                  {' - '}
                  {selectedCapability?.name || `${selectedBuild.detected_framework || 'Unknown'} / ${selectedBuild.detected_runtime || 'Unknown'}`}
                </span>
              </div>
            )}

            <div className="health-check-grid" style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 2fr)',
              gap: '12px',
              marginBottom: '16px'
            }}>
              <div>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '6px'
                }}>
                  Health Port
                </label>
                <input
                  type="number"
                  min="1"
                  max="65535"
                  value={healthCheckPort}
                  onChange={(e) => setHealthCheckPort(e.target.value)}
                  placeholder="Optional"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{
                  display: 'block',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '6px'
                }}>
                  Health Path
                </label>
                <input
                  type="text"
                  value={healthCheckPath}
                  onChange={(e) => setHealthCheckPath(e.target.value)}
                  placeholder="/"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px'
                  }}
                />
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
                Project ID
              </label>
              <input
                type="number"
                value={selectedBuild?.project_id || ''}
                placeholder="Auto-filled from build"
                readOnly
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: '#f9fafb'
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
                value={selectedBuild?.project_name || ''}
                placeholder="Auto-filled from build"
                readOnly
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: '#f9fafb'
                }}
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
                  value={selectedBuild?.branch || ''}
                  placeholder="Auto-filled from build"
                  readOnly
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px',
                    outline: 'none',
                    backgroundColor: '#f9fafb'
                  }}
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
                disabled
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none',
                  backgroundColor: '#f3f4f6',
                  color: '#374151'
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
                        disabled
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
                        disabled
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
                        placeholder="nginx:latest"
                        readOnly
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          fontFamily: 'monospace',
                          backgroundColor: '#f3f4f6',
                          color: '#6b7280'
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
                        placeholder="docker-compose.yml"
                        readOnly
                        style={{
                          width: '100%',
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '6px',
                          fontSize: '14px',
                          outline: 'none',
                          transition: 'border-color 0.2s',
                          fontFamily: 'monospace',
                          backgroundColor: '#f3f4f6',
                          color: '#6b7280'
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
              <div style={{ position: 'relative' }}>
                <textarea
                  value={deployScript}
                  onChange={handleDeployScriptChange}
                  onKeyDown={handleDeployScriptKeyDown}
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
                    backgroundColor: '#fafafa',
                    color: deployScript ? '#111827' : 'transparent'
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
                {deployScriptSuggestion && !deployScript && (
                  <div style={{
                    position: 'absolute',
                    top: '10px',
                    left: '12px',
                    right: '12px',
                    bottom: '10px',
                    pointerEvents: 'none',
                    fontSize: '13px',
                    fontFamily: 'monospace',
                    color: '#9ca3af',
                    whiteSpace: 'pre-wrap',
                    wordWrap: 'break-word',
                    overflow: 'hidden',
                    lineHeight: '1.5'
                  }}>
                    {deployScriptSuggestion}
                  </div>
                )}
              </div>
              <div style={{
                fontSize: '12px',
                color: '#6b7280',
                marginTop: '4px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>
                  {deployType === 'docker' ? 'Optional: override default deploy. Image transfer (save/load) is automatic.' : 'Custom deployment commands. Artifact upload and service restart are automatic.'}
                </span>
                {deployScriptSuggestion && !deployScript && (
                  <span style={{ color: '#6b7280', fontStyle: 'italic' }}>
                    Press Tab to accept suggestion, Esc to dismiss
                  </span>
                )}
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
              disabled={startDisabled}
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: startDisabled ? '#9ca3af' : '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '600',
                cursor: startDisabled ? 'not-allowed' : 'pointer',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                if (!startDisabled) {
                  e.target.style.backgroundColor = '#059669'
                }
              }}
              onMouseLeave={(e) => {
                if (!startDisabled) {
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

              {/* Deploy Timeline */}
              {currentDeploy && stages.length > 0 && (
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
                      Deploy Timeline
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
                            fetchStageLog(currentDeploy.id, stage.stage_name)
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
                    <DeployLog log={log} loading={logLoading} />
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
                  <DeployLog log={stageLog} loading={false} />
                </div>
              )}

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
