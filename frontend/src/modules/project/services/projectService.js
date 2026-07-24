import api from '../../../shared/services/api'

export const projectService = {
  getProjects: async (params = {}) => {
    const response = await api.get('/projects', { params })
    return response.data
  },

  getProject: async (projectId) => {
    const response = await api.get(`/projects/${projectId}`)
    return response.data
  },

  createProject: async (data) => {
    const response = await api.post('/projects', data)
    return response.data
  },

  updateProject: async (projectId, data) => {
    const response = await api.put(`/projects/${projectId}`, data)
    return response.data
  },

  deleteProject: async (projectId) => {
    await api.delete(`/projects/${projectId}`)
  },
}
