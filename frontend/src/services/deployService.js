import api from './api'

export const deployService = {
  getCapabilities: async () => {
    const response = await api.get('/deploy/capabilities')
    return response.data
  },

  startDeploy: async (data) => {
    const response = await api.post('/deploy/start', data)
    return response.data
  },

  getDeployStatus: async (deployId) => {
    const response = await api.get(`/deploy/status/${deployId}`)
    return response.data
  },

  getDeployLog: async (deployId) => {
    const response = await api.get(`/deploy/log/${deployId}`)
    return response.data
  },

  getDeployHistory: async (params = {}) => {
    const response = await api.get('/deploy/history', { params })
    return response.data
  },
}
