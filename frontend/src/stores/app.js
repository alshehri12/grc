import { defineStore } from 'pinia'
import { useI18n } from 'vue-i18n'

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
        direction: (state) => state.locale === 'ar' ? 'rtl' : 'ltr'
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
