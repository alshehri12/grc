import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json'
    }
})

// Request interceptor to add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config
        
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true
            
            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken) {
                try {
                    const response = await axios.post(
                        `${api.defaults.baseURL}/auth/token/refresh/`,
                        { refresh: refreshToken }
                    )
                    
                    const { access } = response.data
                    localStorage.setItem('access_token', access)
                    
                    originalRequest.headers.Authorization = `Bearer ${access}`
                    return api(originalRequest)
                } catch (refreshError) {
                    // Refresh failed, redirect to login
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    window.location.href = '/auth/login'
                }
            }
        }
        
        return Promise.reject(error)
    }
)

export default api

// API endpoints
export const authApi = {
    login: (credentials) => api.post('/auth/token/', credentials),
    refresh: (refresh) => api.post('/auth/token/refresh/', { refresh }),
    verify: (token) => api.post('/auth/token/verify/', { token }),
    me: () => api.get('/core/profiles/me/')
}

export const coreApi = {
    organizations: {
        list: (params) => api.get('/core/organizations/', { params }),
        get: (id) => api.get(`/core/organizations/${id}/`),
        create: (data) => api.post('/core/organizations/', data),
        update: (id, data) => api.put(`/core/organizations/${id}/`, data),
        delete: (id) => api.delete(`/core/organizations/${id}/`)
    },
    departments: {
        list: (params) => api.get('/core/departments/', { params }),
        tree: (orgId) => api.get('/core/departments/tree/', { params: { organization: orgId } })
    },
    users: {
        list: (params) => api.get('/core/users/', { params })
    }
}

export const governanceApi = {
    policies: {
        list: (params) => api.get('/governance/policies/', { params }),
        get: (id) => api.get(`/governance/policies/${id}/`),
        create: (data) => api.post('/governance/policies/', data),
        update: (id, data) => api.put(`/governance/policies/${id}/`, data),
        delete: (id) => api.delete(`/governance/policies/${id}/`),
        submitForReview: (id) => api.post(`/governance/policies/${id}/submit_for_review/`),
        approve: (id) => api.post(`/governance/policies/${id}/approve/`),
        publish: (id) => api.post(`/governance/policies/${id}/publish/`)
    },
    procedures: {
        list: (params) => api.get('/governance/procedures/', { params }),
        get: (id) => api.get(`/governance/procedures/${id}/`)
    },
    documents: {
        list: (params) => api.get('/governance/documents/', { params }),
        get: (id) => api.get(`/governance/documents/${id}/`)
    }
}

export const riskApi = {
    risks: {
        list: (params) => api.get('/risk/risks/', { params }),
        get: (id) => api.get(`/risk/risks/${id}/`),
        create: (data) => api.post('/risk/risks/', data),
        update: (id, data) => api.put(`/risk/risks/${id}/`, data),
        delete: (id) => api.delete(`/risk/risks/${id}/`),
        matrix: (orgId) => api.get('/risk/risks/matrix/', { params: { organization: orgId } }),
        statistics: (orgId) => api.get('/risk/risks/statistics/', { params: { organization: orgId } })
    },
    assets: {
        list: (params) => api.get('/risk/assets/', { params })
    },
    categories: {
        list: () => api.get('/risk/risk-categories/')
    }
}

export const bcmApi = {
    functions: {
        list: (params) => api.get('/bcm/functions/', { params }),
        get: (id) => api.get(`/bcm/functions/${id}/`),
        create: (data) => api.post('/bcm/functions/', data),
        update: (id, data) => api.put(`/bcm/functions/${id}/`, data),
        delete: (id) => api.delete(`/bcm/functions/${id}/`),
        hierarchy: (orgId) => api.get('/bcm/functions/hierarchy/', { params: { organization: orgId } })
    },
    plans: {
        list: (params) => api.get('/bcm/bc-plans/', { params }),
        get: (id) => api.get(`/bcm/bc-plans/${id}/`),
        create: (data) => api.post('/bcm/bc-plans/', data),
        update: (id, data) => api.put(`/bcm/bc-plans/${id}/`, data),
        delete: (id) => api.delete(`/bcm/bc-plans/${id}/`)
    },
    drPlans: {
        list: (params) => api.get('/bcm/dr-plans/', { params }),
        get: (id) => api.get(`/bcm/dr-plans/${id}/`),
        create: (data) => api.post('/bcm/dr-plans/', data),
        update: (id, data) => api.put(`/bcm/dr-plans/${id}/`, data),
        delete: (id) => api.delete(`/bcm/dr-plans/${id}/`)
    },
    bia: {
        list: (params) => api.get('/bcm/bia/', { params }),
        get: (id) => api.get(`/bcm/bia/${id}/`),
        create: (data) => api.post('/bcm/bia/', data),
        update: (id, data) => api.put(`/bcm/bia/${id}/`, data),
        delete: (id) => api.delete(`/bcm/bia/${id}/`)
    },
    tests: {
        list: (params) => api.get('/bcm/tests/', { params }),
        get: (id) => api.get(`/bcm/tests/${id}/`),
        create: (data) => api.post('/bcm/tests/', data),
        update: (id, data) => api.put(`/bcm/tests/${id}/`, data),
        delete: (id) => api.delete(`/bcm/tests/${id}/`)
    },
    incidents: {
        list: (params) => api.get('/bcm/incidents/', { params }),
        get: (id) => api.get(`/bcm/incidents/${id}/`),
        create: (data) => api.post('/bcm/incidents/', data),
        update: (id, data) => api.put(`/bcm/incidents/${id}/`, data),
        delete: (id) => api.delete(`/bcm/incidents/${id}/`)
    }
}

export const complianceApi = {
    frameworks: {
        list: (params) => api.get('/compliance/frameworks/', { params }),
        get: (id) => api.get(`/compliance/frameworks/${id}/`),
        create: (data) => api.post('/compliance/frameworks/', data),
        update: (id, data) => api.put(`/compliance/frameworks/${id}/`, data),
        delete: (id) => api.delete(`/compliance/frameworks/${id}/`)
    },
    controls: {
        list: (params) => api.get('/compliance/controls/', { params }),
        get: (id) => api.get(`/compliance/controls/${id}/`),
        create: (data) => api.post('/compliance/controls/', data),
        update: (id, data) => api.put(`/compliance/controls/${id}/`, data),
        delete: (id) => api.delete(`/compliance/controls/${id}/`),
        byFramework: (frameworkId) => api.get('/compliance/controls/by_framework/', { params: { framework: frameworkId } })
    },
    implementations: {
        list: (params) => api.get('/compliance/implementations/', { params }),
        get: (id) => api.get(`/compliance/implementations/${id}/`),
        create: (data) => api.post('/compliance/implementations/', data),
        update: (id, data) => api.put(`/compliance/implementations/${id}/`, data),
        delete: (id) => api.delete(`/compliance/implementations/${id}/`),
        statistics: (params) => api.get('/compliance/implementations/statistics/', { params })
    },
    audits: {
        list: (params) => api.get('/compliance/audits/', { params }),
        get: (id) => api.get(`/compliance/audits/${id}/`),
        create: (data) => api.post('/compliance/audits/', data),
        update: (id, data) => api.put(`/compliance/audits/${id}/`, data),
        delete: (id) => api.delete(`/compliance/audits/${id}/`)
    },
    findings: {
        list: (params) => api.get('/compliance/findings/', { params }),
        get: (id) => api.get(`/compliance/findings/${id}/`),
        create: (data) => api.post('/compliance/findings/', data),
        update: (id, data) => api.put(`/compliance/findings/${id}/`, data),
        delete: (id) => api.delete(`/compliance/findings/${id}/`),
        open: (orgId) => api.get('/compliance/findings/open_findings/', { params: { organization: orgId } })
    },
    evidence: {
        list: (params) => api.get('/compliance/evidence/', { params }),
        get: (id) => api.get(`/compliance/evidence/${id}/`),
        create: (data) => api.post('/compliance/evidence/', data),
        update: (id, data) => api.put(`/compliance/evidence/${id}/`, data),
        delete: (id) => api.delete(`/compliance/evidence/${id}/`),
        expiringSoon: (orgId) => api.get('/compliance/evidence/expiring_soon/', { params: { organization: orgId } })
    },
    gapAssessments: {
        list: (params) => api.get('/compliance/gap-assessments/', { params }),
        get: (id) => api.get(`/compliance/gap-assessments/${id}/`),
        create: (data) => api.post('/compliance/gap-assessments/', data),
        update: (id, data) => api.put(`/compliance/gap-assessments/${id}/`, data),
        delete: (id) => api.delete(`/compliance/gap-assessments/${id}/`)
    }
}

export const dashboardApi = {
    executiveSummary: (orgId) => api.get('/dashboard/dashboards/executive_summary/', { params: { organization: orgId } }),
    myDashboards: () => api.get('/dashboard/dashboards/my_dashboards/'),
    kpis: {
        latest: (orgId) => api.get('/dashboard/kpi-values/latest/', { params: { organization: orgId } })
    }
}

export const workflowApi = {
    tasks: {
        myTasks: () => api.get('/workflow/tasks/my_tasks/'),
        start: (id) => api.post(`/workflow/tasks/${id}/start/`),
        complete: (id, notes) => api.post(`/workflow/tasks/${id}/complete/`, { notes })
    },
    approvals: {
        myPending: () => api.get('/workflow/approvals/my_pending/'),
        approve: (id, comments) => api.post(`/workflow/approvals/${id}/approve/`, { comments }),
        reject: (id, comments) => api.post(`/workflow/approvals/${id}/reject/`, { comments })
    }
}

export const notificationsApi = {
    myNotifications: (unread) => api.get('/notifications/notifications/my_notifications/', { params: { unread } }),
    unreadCount: () => api.get('/notifications/notifications/unread_count/'),
    markRead: (id) => api.post(`/notifications/notifications/${id}/mark_read/`),
    markAllRead: () => api.post('/notifications/notifications/mark_all_read/')
}
