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
}
