import api from '../../../shared/services/api'

export const authService = {
  async login(username, password) {
    const form = new URLSearchParams()
    form.set('grant_type', 'password')
    form.set('username', username)
    form.set('password', password)
    form.set('scope', '')

    const response = await api.post('/auth/login', form, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  async getCurrentAdmin() {
    const response = await api.get('/auth/me')
    return response.data
  },
}
