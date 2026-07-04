import api from './api'

export const buildService = {
  startBuild: async (data) => {
    const response = await api.post('/build/start', data)
    return response.data
  },

  getBuildStatus: async (buildId) => {
    const response = await api.get(`/build/status/${buildId}`)
    return response.data
  },

  getBuildLog: async (buildId) => {
    const response = await api.get(`/build/log/${buildId}`)
    return response.data
  },

  getBuildHistory: async (params = {}) => {
    const response = await api.get('/build/history', { params })
    return response.data
  },
}
