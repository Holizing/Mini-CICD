import { useEffect, useMemo, useState } from 'react'

import ProjectForm from '../components/ProjectForm'
import ProjectTable from '../components/ProjectTable'
import { projectService } from '../services/projectService'

const formatApiError = (err, fallback) => {
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(', ')
  }
  return detail || fallback
}

const Projects = () => {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [projectToDelete, setProjectToDelete] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const fetchProjects = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await projectService.getProjects()
      setProjects(response.projects || [])
    } catch (err) {
      setError(formatApiError(err, 'Failed to load projects'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const filteredProjects = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()

    return projects.filter((project) => {
      const matchesSearch = !term || [
        project.name,
        project.repo_url,
        project.branch,
        project.service_name,
      ].some((value) => (value || '').toLowerCase().includes(term))

      const matchesStatus = statusFilter === 'all' || project.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [projects, searchTerm, statusFilter])

  const activeCount = projects.filter((project) => project.status === 'active').length

  const handleSubmit = async (payload) => {
    try {
      setSaving(true)
      setError('')
      setMessage('')

      if (selectedProject) {
        await projectService.updateProject(selectedProject.id, payload)
        setMessage('Project updated successfully')
      } else {
        await projectService.createProject(payload)
        setMessage('Project created successfully')
      }

      setSelectedProject(null)
      await fetchProjects()
    } catch (err) {
      setError(formatApiError(err, 'Failed to save project'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!projectToDelete) return

    try {
      setDeleting(true)
      setError('')
      setMessage('')
      await projectService.deleteProject(projectToDelete.id)

      if (selectedProject?.id === projectToDelete.id) {
        setSelectedProject(null)
      }

      setProjectToDelete(null)
      setMessage('Project deleted successfully')
      await fetchProjects()
    } catch (err) {
      setError(formatApiError(err, 'Failed to delete project'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
      }}>
        <h1 style={{
          fontSize: '28px',
          fontWeight: '700',
          color: '#111827',
          margin: 0,
        }}>
          Projects
        </h1>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
        gap: '16px',
        marginBottom: '24px',
      }}>
        {[
          ['Total Projects', projects.length],
          ['Active', activeCount],
          ['Inactive', projects.length - activeCount],
        ].map(([label, value]) => (
          <div
            key={label}
            style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '18px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div style={{ color: '#6b7280', fontSize: '13px', marginBottom: '8px' }}>
              {label}
            </div>
            <div style={{ color: '#111827', fontSize: '28px', fontWeight: '700' }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div style={{
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          padding: '12px',
          borderRadius: '6px',
          marginBottom: '16px',
          fontSize: '14px',
        }}>
          {error}
        </div>
      )}

      {message && (
        <div style={{
          backgroundColor: '#dcfce7',
          color: '#166534',
          padding: '12px',
          borderRadius: '6px',
          marginBottom: '16px',
          fontSize: '14px',
        }}>
          {message}
        </div>
      )}

      {projectToDelete && (
        <div style={{
          backgroundColor: '#fff7ed',
          color: '#9a3412',
          padding: '16px',
          border: '1px solid #fed7aa',
          borderRadius: '8px',
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
        }}>
          <div>
            Delete <strong>{projectToDelete.name}</strong>? This removes the project record from Mini CI/CD.
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              onClick={() => setProjectToDelete(null)}
              disabled={deleting}
              style={{
                padding: '8px 12px',
                backgroundColor: 'white',
                color: '#374151',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontWeight: '600',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              style={{
                padding: '8px 12px',
                backgroundColor: deleting ? '#fca5a5' : '#dc2626',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: '600',
              }}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
      )}

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        marginBottom: '24px',
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '700',
          color: '#374151',
          marginTop: 0,
          marginBottom: '16px',
        }}>
          {selectedProject ? 'Edit Project' : 'Create Project'}
        </h2>
        <ProjectForm
          selectedProject={selectedProject}
          onSubmit={handleSubmit}
          onCancel={() => setSelectedProject(null)}
          loading={saving}
        />
      </div>

      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}>
        <h2 style={{
          fontSize: '18px',
          fontWeight: '700',
          color: '#374151',
          marginTop: 0,
          marginBottom: '16px',
        }}>
          Project List
        </h2>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 180px',
          gap: '12px',
          marginBottom: '16px',
        }}>
          <input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search by name, repo, branch, or service"
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px',
            }}
          />
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px',
              backgroundColor: 'white',
            }}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        {loading ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#6b7280' }}>
            Loading...
          </div>
        ) : (
          <ProjectTable
            projects={filteredProjects}
            onEdit={(project) => {
              setSelectedProject(project)
              setProjectToDelete(null)
            }}
            onDelete={setProjectToDelete}
            deletingId={projectToDelete?.id}
          />
        )}
      </div>
    </div>
  )
}

export default Projects
