const ProjectTable = ({ projects, onEdit, onDelete, deletingId }) => {
  if (!projects || projects.length === 0) {
    return (
      <div style={{
        padding: '32px',
        textAlign: 'center',
        color: '#6b7280',
      }}>
        No projects available
      </div>
    )
  }

  return (
    <div style={{
      overflowX: 'auto',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      backgroundColor: 'white',
    }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        fontSize: '14px',
      }}>
        <thead>
          <tr style={{
            backgroundColor: '#f9fafb',
            borderBottom: '1px solid #e5e7eb',
          }}>
            {['Name', 'Repository', 'Branch', 'Deploy Path', 'Service', 'Status', 'Actions'].map((header) => (
              <th
                key={header}
                style={{
                  padding: '12px 16px',
                  textAlign: 'left',
                  fontWeight: '700',
                  color: '#374151',
                }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {projects.map((project) => (
            <tr
              key={project.id}
              style={{ borderBottom: '1px solid #e5e7eb' }}
            >
              <td style={{ padding: '12px 16px', fontWeight: '600' }}>
                {project.name}
              </td>
              <td style={{
                padding: '12px 16px',
                color: '#4b5563',
                maxWidth: '280px',
                wordBreak: 'break-word',
              }}>
                {project.repo_url}
              </td>
              <td style={{ padding: '12px 16px', color: '#4b5563' }}>
                {project.branch}
              </td>
              <td style={{ padding: '12px 16px', color: '#4b5563' }}>
                {project.deploy_path}
              </td>
              <td style={{ padding: '12px 16px', color: '#4b5563' }}>
                {project.service_name}
              </td>
              <td style={{ padding: '12px 16px' }}>
                <span style={{
                  display: 'inline-flex',
                  padding: '4px 8px',
                  borderRadius: '999px',
                  backgroundColor: project.status === 'active' ? '#dcfce7' : '#f3f4f6',
                  color: project.status === 'active' ? '#166534' : '#4b5563',
                  fontSize: '12px',
                  fontWeight: '700',
                }}>
                  {project.status}
                </span>
              </td>
              <td style={{ padding: '12px 16px' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => onEdit(project)}
                    style={{
                      padding: '7px 10px',
                      backgroundColor: '#eff6ff',
                      color: '#1d4ed8',
                      border: '1px solid #bfdbfe',
                      borderRadius: '6px',
                      fontWeight: '600',
                    }}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(project)}
                    disabled={deletingId === project.id}
                    style={{
                      padding: '7px 10px',
                      backgroundColor: deletingId === project.id ? '#fee2e2' : '#fef2f2',
                      color: '#b91c1c',
                      border: '1px solid #fecaca',
                      borderRadius: '6px',
                      fontWeight: '600',
                    }}
                  >
                    {deletingId === project.id ? 'Confirm?' : 'Delete'}
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ProjectTable
