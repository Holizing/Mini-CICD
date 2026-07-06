import { useEffect, useState } from 'react'

const emptyForm = {
  name: '',
  repo_url: '',
  branch: 'main',
  description: '',
  deploy_path: '',
  service_name: '',
  status: 'active',
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #d1d5db',
  borderRadius: '6px',
  fontSize: '14px',
  outline: 'none',
}

const labelStyle = {
  display: 'block',
  fontSize: '14px',
  fontWeight: '600',
  color: '#374151',
  marginBottom: '6px',
}

const ProjectForm = ({ selectedProject, onSubmit, onCancel, loading }) => {
  const [form, setForm] = useState(emptyForm)

  useEffect(() => {
    if (selectedProject) {
      setForm({
        name: selectedProject.name || '',
        repo_url: selectedProject.repo_url || '',
        branch: selectedProject.branch || 'main',
        description: selectedProject.description || '',
        deploy_path: selectedProject.deploy_path || '',
        service_name: selectedProject.service_name || '',
        status: selectedProject.status || 'active',
      })
    } else {
      setForm(emptyForm)
    }
  }, [selectedProject])

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: '16px',
      }}>
        <div>
          <label style={labelStyle}>Project Name</label>
          <input
            name="name"
            value={form.name}
            onChange={handleChange}
            placeholder="mini-cicd-api"
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>Branch</label>
          <input
            name="branch"
            value={form.branch}
            onChange={handleChange}
            placeholder="main"
            required
            style={inputStyle}
          />
        </div>

        <div style={{ gridColumn: '1 / -1' }}>
          <label style={labelStyle}>Repository URL</label>
          <input
            name="repo_url"
            value={form.repo_url}
            onChange={handleChange}
            placeholder="https://github.com/user/repository.git"
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>Deploy Path</label>
          <input
            name="deploy_path"
            value={form.deploy_path}
            onChange={handleChange}
            placeholder="/var/www/mini-cicd-api"
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>Service Name</label>
          <input
            name="service_name"
            value={form.service_name}
            onChange={handleChange}
            placeholder="mini-cicd-api"
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label style={labelStyle}>Status</label>
          <select
            name="status"
            value={form.status}
            onChange={handleChange}
            style={inputStyle}
          >
            <option value="active">active</option>
            <option value="inactive">inactive</option>
          </select>
        </div>

        <div style={{ gridColumn: '1 / -1' }}>
          <label style={labelStyle}>Description</label>
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="Short note about this project"
            rows={3}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '10px 16px',
            backgroundColor: loading ? '#9ca3af' : '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontWeight: '600',
          }}
        >
          {selectedProject ? 'Update Project' : 'Create Project'}
        </button>

        {selectedProject && (
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: '10px 16px',
              backgroundColor: 'white',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontWeight: '600',
            }}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}

export default ProjectForm
