import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Layouts
import MainLayout from '@/layouts/MainLayout.vue'
import AuthLayout from '@/layouts/AuthLayout.vue'

// Views
const Login = () => import('@/views/auth/Login.vue')
const Dashboard = () => import('@/views/Dashboard.vue')

// Governance
const Policies = () => import('@/views/governance/Policies.vue')
const Procedures = () => import('@/views/governance/Procedures.vue')
const Documents = () => import('@/views/governance/Documents.vue')

// Risk
const RiskRegister = () => import('@/views/risk/RiskRegister.vue')
const RiskMatrix = () => import('@/views/risk/RiskMatrix.vue')

// BCM
const BusinessFunctions = () => import('@/views/bcm/BusinessFunctions.vue')
const BCPlans = () => import('@/views/bcm/BCPlans.vue')
const BIA = () => import('@/views/bcm/BIA.vue')
const DRPlans = () => import('@/views/bcm/DRPlans.vue')
const BCMTests = () => import('@/views/bcm/BCMTests.vue')

// Compliance
const Controls = () => import('@/views/compliance/Controls.vue')
const Audits = () => import('@/views/compliance/Audits.vue')
const Evidence = () => import('@/views/compliance/Evidence.vue')

// Workflow
const TaskInbox = () => import('@/views/workflow/TaskInbox.vue')
const ApprovalCenter = () => import('@/views/workflow/ApprovalCenter.vue')
const WorkflowDashboard = () => import('@/views/workflow/WorkflowDashboard.vue')

// Settings
const Settings = () => import('@/views/Settings.vue')
const Profile = () => import('@/views/Profile.vue')

const routes = [
    {
        path: '/auth',
        component: AuthLayout,
        children: [
            {
                path: 'login',
                name: 'Login',
                component: Login,
                meta: { guest: true }
            }
        ]
    },
    {
        path: '/',
        component: MainLayout,
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                name: 'Dashboard',
                component: Dashboard
            },
            // Governance
            {
                path: 'governance/policies',
                name: 'Policies',
                component: Policies
            },
            {
                path: 'governance/procedures',
                name: 'Procedures',
                component: Procedures
            },
            {
                path: 'governance/documents',
                name: 'Documents',
                component: Documents
            },
            // Risk
            {
                path: 'risk/register',
                name: 'RiskRegister',
                component: RiskRegister
            },
            {
                path: 'risk/matrix',
                name: 'RiskMatrix',
                component: RiskMatrix
            },
            // BCM
            {
                path: 'bcm/functions',
                name: 'BusinessFunctions',
                component: BusinessFunctions
            },
            {
                path: 'bcm/plans',
                name: 'BCPlans',
                component: BCPlans
            },
            {
                path: 'bcm/bia',
                name: 'BIA',
                component: BIA
            },
            {
                path: 'bcm/dr-plans',
                name: 'DRPlans',
                component: DRPlans
            },
            {
                path: 'bcm/tests',
                name: 'BCMTests',
                component: BCMTests
            },
            // Compliance
            {
                path: 'compliance/controls',
                name: 'Controls',
                component: Controls
            },
            {
                path: 'compliance/audits',
                name: 'Audits',
                component: Audits
            },
            {
                path: 'compliance/evidence',
                name: 'Evidence',
                component: Evidence
            },
            // Workflow
            {
                path: 'workflow',
                name: 'WorkflowDashboard',
                component: WorkflowDashboard
            },
            {
                path: 'workflow/tasks',
                name: 'TaskInbox',
                component: TaskInbox
            },
            {
                path: 'workflow/approvals',
                name: 'ApprovalCenter',
                component: ApprovalCenter
            },
            // Settings
            {
                path: 'settings',
                name: 'Settings',
                component: Settings
            },
            {
                path: 'profile',
                name: 'Profile',
                component: Profile
            }
        ]
    },
    {
        path: '/:pathMatch(.*)*',
        redirect: '/'
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
    const authStore = useAuthStore()
    
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next({ name: 'Login' })
    } else if (to.meta.guest && authStore.isAuthenticated) {
        next({ name: 'Dashboard' })
    } else {
        next()
    }
})

export default router
