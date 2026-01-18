import { defineStore } from 'pinia'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null,
        accessToken: localStorage.getItem('access_token') || null,
        refreshToken: localStorage.getItem('refresh_token') || null,
        loading: false,
        error: null
    }),
    
    getters: {
        isAuthenticated: (state) => !!state.accessToken,
        currentUser: (state) => state.user,
        userFullName: (state) => {
            if (state.user) {
                return state.user.first_name && state.user.last_name
                    ? `${state.user.first_name} ${state.user.last_name}`
                    : state.user.username
            }
            return ''
        }
    },
    
    actions: {
        async login(username, password) {
            this.loading = true
            this.error = null
            
            try {
                const response = await authApi.login({ username, password })
                const { access, refresh } = response.data
                
                this.accessToken = access
                this.refreshToken = refresh
                
                localStorage.setItem('access_token', access)
                localStorage.setItem('refresh_token', refresh)
                
                await this.fetchUser()
                
                return true
            } catch (error) {
                this.error = error.response?.data?.detail || 'Login failed'
                return false
            } finally {
                this.loading = false
            }
        },
        
        async fetchUser() {
            try {
                const response = await authApi.me()
                this.user = response.data
            } catch (error) {
                console.error('Failed to fetch user:', error)
            }
        },
        
        async logout() {
            this.user = null
            this.accessToken = null
            this.refreshToken = null
            
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
        },
        
        async initialize() {
            if (this.accessToken) {
                await this.fetchUser()
            }
        }
    }
})
