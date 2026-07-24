import api from '../../../shared/services/api'


export const automationService = {
  async getDeliveries(params = {}) {
    const response = await api.get('/webhooks/deliveries', { params })
    return response.data
  },

  async getDelivery(deliveryId) {
    const response = await api.get(`/webhooks/deliveries/${deliveryId}`)
    return response.data
  },
}
