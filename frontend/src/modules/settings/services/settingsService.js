import api from '../../../shared/services/api'

export const settingsService = {
  async getSettings() {
    const response = await api.get('/settings')
    return response.data
  },

  async updateSettings(payload) {
    const response = await api.put('/settings', payload)
    return response.data
  },

  async resetSettings() {
    const response = await api.post('/settings/reset')
    return response.data
  },

  async getDeploymentTarget() {
    const response = await api.get('/settings/deployment-target')
    return response.data
  },

  async updateDeploymentTarget(payload) {
    const response = await api.put('/settings/deployment-target', payload)
    return response.data
  },

  async testDeploymentTarget() {
    const response = await api.post('/settings/deployment-target/test')
    return response.data
  },
}
