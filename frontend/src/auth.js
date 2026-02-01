/**
 * Authentication utility functions for token management
 */

const TOKEN_KEY = 'newsieai_token'
const USER_KEY = 'newsieai_user'

export const auth = {
  // Save token and user info to localStorage
  setToken(token, user) {
    localStorage.setItem(TOKEN_KEY, token)
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    }
  },

  // Get token from localStorage
  getToken() {
    return localStorage.getItem(TOKEN_KEY)
  },

  // Get user info from localStorage
  getUser() {
    const userStr = localStorage.getItem(USER_KEY)
    return userStr ? JSON.parse(userStr) : null
  },

  // Remove token and user info
  clearAuth() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.getToken()
  },

  // Get authorization header for API calls
  getAuthHeader() {
    const token = this.getToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }
}

