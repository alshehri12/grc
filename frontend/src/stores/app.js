import { defineStore } from 'pinia'
import { coreApi, authApi } from '@/api'

export const useAppStore = defineStore('app', {
    state: () => ({
        locale: localStorage.getItem('locale') || 'en',
        darkMode: localStorage.getItem('darkMode') === 'true',
        sidebarCollapsed: false,
        currentOrganization: localStorage.getItem('currentOrganization') 
            ? JSON.parse(localStorage.getItem('currentOrganization')) 
            : null
    }),
    
    getters: {
        isRTL: (state) => state.locale === 'ar',
        direction: (state) => state.locale === 'ar' ? 'rtl' : 'ltr',
        organizationId: (state) => {
            const inState = Number(state.currentOrganization?.id)
            if (inState) return inState
            try {
                const local = JSON.parse(localStorage.getItem('currentOrganization') || 'null')
                const localId = Number(local?.id)
                return localId || null
            } catch (error) {
                return null
            }
        }
    },
    
    actions: {
        setLocale(locale) {
            this.locale = locale
            localStorage.setItem('locale', locale)
            
            // Update document direction
            document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr'
            document.documentElement.lang = locale
            
            // Update HTML class for RTL
            if (locale === 'ar') {
                document.documentElement.classList.add('rtl')
            } else {
                document.documentElement.classList.remove('rtl')
            }
        },
        
        toggleDarkMode() {
            this.darkMode = !this.darkMode
            localStorage.setItem('darkMode', this.darkMode.toString())
            
            if (this.darkMode) {
                document.documentElement.classList.add('dark-mode')
            } else {
                document.documentElement.classList.remove('dark-mode')
            }
        },
        
        setDarkMode(value) {
            this.darkMode = value
            localStorage.setItem('darkMode', value.toString())
            
            if (value) {
                document.documentElement.classList.add('dark-mode')
            } else {
                document.documentElement.classList.remove('dark-mode')
            }
        },
        
        toggleSidebar() {
            this.sidebarCollapsed = !this.sidebarCollapsed
        },
        
        setOrganization(org) {
            this.currentOrganization = org
            if (org) {
                localStorage.setItem('currentOrganization', JSON.stringify(org))
            } else {
                localStorage.removeItem('currentOrganization')
            }
        },

        async ensureOrganization() {
            // 1) Use existing selected organization if available.
            if (this.organizationId) {
                return this.organizationId
            }

            // 2) Try loading organizations and auto-select first available.
            try {
                const response = await coreApi.organizations.list()
                const organizations = response.data?.results || response.data || []
                if (Array.isArray(organizations) && organizations.length > 0) {
                    const selected = organizations.find((org) => org.is_active !== false) || organizations[0]
                    this.setOrganization(selected)
                    return Number(selected.id) || null
                }

                // 2.1) No organizations exist: create a default one so org-scoped forms can work.
                const now = Date.now()
                const createResponse = await coreApi.organizations.create({
                    name: 'Default Organization',
                    name_ar: 'المنظمة الافتراضية',
                    code: `ORG-${now}`
                })
                const created = createResponse.data
                if (created?.id) {
                    this.setOrganization(created)
                    return Number(created.id)
                }
            } catch (error) {
                console.error('Failed to ensure organization:', error)
            }

            // 3) Fallback: derive organization from current user profile.
            try {
                const meResponse = await authApi.me()
                const profile = meResponse.data?.profile
                const profileOrgId = Number(profile?.organization)
                if (profileOrgId) {
                    this.setOrganization({
                        id: profileOrgId,
                        name: profile?.organization_name || `Org #${profileOrgId}`
                    })
                    return profileOrgId
                }
            } catch (error) {
                console.error('Failed to derive organization from profile:', error)
            }

            return null
        },
        
        initialize() {
            // Initialize theme
            if (this.darkMode) {
                document.documentElement.classList.add('dark-mode')
            }
            
            // Initialize direction
            document.documentElement.dir = this.locale === 'ar' ? 'rtl' : 'ltr'
            document.documentElement.lang = this.locale
            
            if (this.locale === 'ar') {
                document.documentElement.classList.add('rtl')
            }
        }
    }
})
