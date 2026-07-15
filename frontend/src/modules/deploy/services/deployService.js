import api from '../../../shared/services/api'

export const deployService = {
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

  getDeployStages: async (deployId) => {
    const response = await api.get(`/deploy/stages/${deployId}`)
    return response.data
  },

  getStageLog: async (deployId, stageName) => {
    const response = await api.get(`/deploy/stage/${deployId}/${encodeURIComponent(stageName)}`)
    return response.data
  },
}
