<template>
    <div class="workflow-dashboard">
        <div class="page-header">
            <div>
                <h1>Workflow Dashboard</h1>
                <p class="page-subtitle">لوحة معلومات سير العمل - Overview of workflows and tasks</p>
            </div>
        </div>
        
        <!-- Quick Stats -->
        <div class="stats-grid">
            <Card class="stat-card pending-approvals">
                <template #content>
                    <div class="stat-content">
                        <div class="stat-icon">
                            <i class="pi pi-check-square"></i>
                        </div>
                        <div class="stat-info">
                            <span class="stat-value">{{ stats.pendingApprovals }}</span>
                            <span class="stat-label">Pending Approvals</span>
                        </div>
                    </div>
                </template>
            </Card>
            
            <Card class="stat-card active-tasks">
                <template #content>
                    <div class="stat-content">
                        <div class="stat-icon">
                            <i class="pi pi-inbox"></i>
                        </div>
                        <div class="stat-info">
                            <span class="stat-value">{{ stats.activeTasks }}</span>
                            <span class="stat-label">Active Tasks</span>
                        </div>
                    </div>
                </template>
            </Card>
            
            <Card class="stat-card overdue-items">
                <template #content>
                    <div class="stat-content">
                        <div class="stat-icon">
                            <i class="pi pi-exclamation-triangle"></i>
                        </div>
                        <div class="stat-info">
                            <span class="stat-value">{{ stats.overdueItems }}</span>
                            <span class="stat-label">Overdue Items</span>
                        </div>
                    </div>
                </template>
            </Card>
            
            <Card class="stat-card completed-today">
                <template #content>
                    <div class="stat-content">
                        <div class="stat-icon">
                            <i class="pi pi-check-circle"></i>
                        </div>
                        <div class="stat-info">
                            <span class="stat-value">{{ stats.completedToday }}</span>
                            <span class="stat-label">Completed Today</span>
                        </div>
                    </div>
                </template>
            </Card>
        </div>
        
        <!-- Two Column Layout -->
        <div class="dashboard-grid">
            <!-- Pending Approvals -->
            <Card>
                <template #title>
                    <div class="card-header">
                        <span>My Pending Approvals</span>
                        <router-link to="/workflow/approvals" class="view-all-link">View All →</router-link>
                    </div>
                </template>
                <template #content>
                    <div class="items-list" v-if="pendingApprovals.length">
                        <div 
                            v-for="approval in pendingApprovals.slice(0, 5)" 
                            :key="approval.id"
                            class="list-item"
                            :class="{ overdue: isOverdue(approval.due_date) }"
                        >
                            <div class="item-info">
                                <span class="item-title">{{ approval.workflow_title }}</span>
                                <span class="item-meta">{{ approval.step_name }} • Due: {{ formatDate(approval.due_date) }}</span>
                            </div>
                            <div class="item-actions">
                                <Button icon="pi pi-check" text rounded severity="success" size="small" @click="quickApprove(approval)" v-tooltip="'Approve'" />
                                <Button icon="pi pi-times" text rounded severity="danger" size="small" @click="quickReject(approval)" v-tooltip="'Reject'" />
                            </div>
                        </div>
                    </div>
                    <div class="empty-state" v-else>
                        <i class="pi pi-check-circle"></i>
                        <p>All caught up!</p>
                    </div>
                </template>
            </Card>
            
            <!-- Active Tasks -->
            <Card>
                <template #title>
                    <div class="card-header">
                        <span>My Tasks</span>
                        <router-link to="/workflow/tasks" class="view-all-link">View All →</router-link>
                    </div>
                </template>
                <template #content>
                    <div class="items-list" v-if="activeTasks.length">
                        <div 
                            v-for="task in activeTasks.slice(0, 5)" 
                            :key="task.id"
                            class="list-item"
                            :class="{ overdue: isOverdue(task.due_date) }"
                        >
                            <div class="item-info">
                                <span class="item-title">{{ task.title }}</span>
                                <span class="item-meta">
                                    <Tag :severity="getPrioritySeverity(task.priority)" size="small">{{ task.priority }}</Tag>
                                    • Due: {{ formatDate(task.due_date) }}
                                </span>
                            </div>
                            <div class="item-actions">
                                <Button 
                                    v-if="task.status === 'pending'"
                                    icon="pi pi-play" 
                                    text 
                                    rounded 
                                    size="small" 
                                    @click="startTask(task)" 
                                    v-tooltip="'Start'"
                                />
                                <Button 
                                    v-if="task.status === 'in_progress'"
                                    icon="pi pi-check" 
                                    text 
                                    rounded 
                                    severity="success" 
                                    size="small" 
                                    @click="completeTask(task)" 
                                    v-tooltip="'Complete'"
                                />
                            </div>
                        </div>
                    </div>
                    <div class="empty-state" v-else>
                        <i class="pi pi-inbox"></i>
                        <p>No active tasks</p>
                    </div>
                </template>
            </Card>
        </div>
        
        <!-- Recent Activity -->
        <Card>
            <template #title>Recent Activity</template>
            <template #content>
                <div class="activity-timeline" v-if="recentActivity.length">
                    <div v-for="activity in recentActivity" :key="activity.id" class="activity-item">
                        <div class="activity-icon" :class="activity.type">
                            <i :class="getActivityIcon(activity.type)"></i>
                        </div>
                        <div class="activity-content">
                            <span class="activity-title">{{ activity.title }}</span>
                            <span class="activity-time">{{ formatRelativeTime(activity.created_at) }}</span>
                        </div>
                    </div>
                </div>
                <div class="empty-state" v-else>
                    <i class="pi pi-history"></i>
                    <p>No recent activity</p>
                </div>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { workflowApi } from '@/api'

const toast = useToast()

const pendingApprovals = ref([])
const activeTasks = ref([])
const recentActivity = ref([])
const loading = ref(false)

const stats = computed(() => ({
    pendingApprovals: pendingApprovals.value.length,
    activeTasks: activeTasks.value.filter(t => t.status !== 'completed').length,
    overdueItems: [...pendingApprovals.value, ...activeTasks.value].filter(item => isOverdue(item.due_date)).length,
    completedToday: activeTasks.value.filter(t => t.status === 'completed' && isToday(t.completed_at)).length
}))

const getPrioritySeverity = (priority) => {
    const map = { low: 'secondary', medium: 'info', high: 'warn', critical: 'danger' }
    return map[priority] || 'info'
}

const getActivityIcon = (type) => {
    const icons = {
        approval: 'pi pi-check',
        rejection: 'pi pi-times',
        task_completed: 'pi pi-check-circle',
        workflow_started: 'pi pi-play',
        escalation: 'pi pi-exclamation-triangle'
    }
    return icons[type] || 'pi pi-circle'
}

const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const formatRelativeTime = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now - date
    
    const minutes = Math.floor(diff / 60000)
    if (minutes < 60) return `${minutes}m ago`
    
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    
    const days = Math.floor(hours / 24)
    return `${days}d ago`
}

const isOverdue = (dateStr) => {
    if (!dateStr) return false
    return new Date(dateStr) < new Date()
}

const isToday = (dateStr) => {
    if (!dateStr) return false
    const date = new Date(dateStr)
    const today = new Date()
    return date.toDateString() === today.toDateString()
}

const loadData = async () => {
    loading.value = true
    try {
        const [approvalsRes, tasksRes] = await Promise.all([
            workflowApi.approvals.myPending(),
            workflowApi.tasks.myTasks()
        ])
        
        pendingApprovals.value = approvalsRes.data.results || approvalsRes.data
        activeTasks.value = tasksRes.data.results || tasksRes.data
        
        // Mock recent activity (would come from API)
        recentActivity.value = []
    } catch (error) {
        console.error('Failed to load dashboard data:', error)
    } finally {
        loading.value = false
    }
}

const quickApprove = async (approval) => {
    try {
        await workflowApi.approvals.approve(approval.id, '')
        toast.add({ severity: 'success', summary: 'Approved', detail: 'Request approved', life: 3000 })
        await loadData()
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to approve', life: 3000 })
    }
}

const quickReject = async (approval) => {
    try {
        await workflowApi.approvals.reject(approval.id, 'Rejected from dashboard')
        toast.add({ severity: 'info', summary: 'Rejected', detail: 'Request rejected', life: 3000 })
        await loadData()
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to reject', life: 3000 })
    }
}

const startTask = async (task) => {
    try {
        await workflowApi.tasks.start(task.id)
        toast.add({ severity: 'success', summary: 'Started', detail: 'Task started', life: 3000 })
        await loadData()
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to start task', life: 3000 })
    }
}

const completeTask = async (task) => {
    try {
        await workflowApi.tasks.complete(task.id, '')
        toast.add({ severity: 'success', summary: 'Completed', detail: 'Task completed', life: 3000 })
        await loadData()
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to complete task', life: 3000 })
    }
}

onMounted(() => {
    loadData()
})
</script>

<style scoped>
.workflow-dashboard {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.page-header h1 {
    margin: 0;
    font-size: 1.5rem;
}

.page-subtitle {
    margin: 0.25rem 0 0;
    color: var(--p-text-muted-color);
    font-size: 0.9rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
}

.stat-card :deep(.p-card-body) {
    padding: 1.25rem;
}

.stat-content {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.stat-icon i {
    font-size: 1.5rem;
    color: white;
}

.pending-approvals .stat-icon { background: linear-gradient(135deg, #f97316, #ea580c); }
.active-tasks .stat-icon { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.overdue-items .stat-icon { background: linear-gradient(135deg, #ef4444, #dc2626); }
.completed-today .stat-icon { background: linear-gradient(135deg, #22c55e, #16a34a); }

.stat-info {
    display: flex;
    flex-direction: column;
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}

.stat-label {
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
    margin-top: 0.25rem;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
}

.view-all-link {
    font-size: 0.85rem;
    color: var(--p-primary-color);
    text-decoration: none;
}

.view-all-link:hover {
    text-decoration: underline;
}

.items-list {
    display: flex;
    flex-direction: column;
}

.list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--p-surface-200);
}

.list-item:last-child {
    border-bottom: none;
}

.list-item.overdue {
    background: rgba(239, 68, 68, 0.05);
    margin: 0 -1rem;
    padding: 0.75rem 1rem;
}

.item-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.item-title {
    font-weight: 500;
}

.item-meta {
    font-size: 0.8rem;
    color: var(--p-text-muted-color);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.item-actions {
    display: flex;
    gap: 0.25rem;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 2rem;
    color: var(--p-text-muted-color);
}

.empty-state i {
    font-size: 2rem;
    opacity: 0.5;
}

.empty-state p {
    margin: 0;
}

.activity-timeline {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.activity-item {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
}

.activity-icon {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--p-surface-100);
}

.activity-icon.approval { color: var(--p-green-500); }
.activity-icon.rejection { color: var(--p-red-500); }
.activity-icon.task_completed { color: var(--p-blue-500); }
.activity-icon.escalation { color: var(--p-orange-500); }

.activity-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.activity-title {
    font-size: 0.9rem;
}

.activity-time {
    font-size: 0.8rem;
    color: var(--p-text-muted-color);
}
</style>
