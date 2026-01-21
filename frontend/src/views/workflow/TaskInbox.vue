<template>
    <div class="task-inbox">
        <div class="page-header">
            <div>
                <h1>{{ $t('workflow.taskInbox') || 'Task Inbox' }}</h1>
                <p class="page-subtitle">صندوق المهام - Manage your assigned tasks</p>
            </div>
        </div>
        
        <!-- Summary Cards -->
        <div class="summary-cards">
            <Card class="summary-card">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-clock text-warning"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ pendingCount }}</span>
                            <span class="summary-label">Pending</span>
                        </div>
                    </div>
                </template>
            </Card>
            <Card class="summary-card">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-spinner text-info"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ inProgressCount }}</span>
                            <span class="summary-label">In Progress</span>
                        </div>
                    </div>
                </template>
            </Card>
            <Card class="summary-card overdue">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-exclamation-triangle text-danger"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ overdueCount }}</span>
                            <span class="summary-label">Overdue</span>
                        </div>
                    </div>
                </template>
            </Card>
            <Card class="summary-card">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-check-circle text-success"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ completedCount }}</span>
                            <span class="summary-label">Completed</span>
                        </div>
                    </div>
                </template>
            </Card>
        </div>
        
        <!-- Filters -->
        <Card class="filters-card">
            <template #content>
                <div class="filters-row">
                    <InputText v-model="filters.search" placeholder="Search tasks..." class="filter-input" @input="loadTasks" />
                    <Dropdown 
                        v-model="filters.status" 
                        :options="statusOptions" 
                        optionLabel="label" 
                        optionValue="value"
                        placeholder="Status" 
                        showClear
                        class="filter-dropdown"
                        @change="loadTasks"
                    />
                    <Dropdown 
                        v-model="filters.priority" 
                        :options="priorityOptions" 
                        optionLabel="label" 
                        optionValue="value"
                        placeholder="Priority" 
                        showClear
                        class="filter-dropdown"
                        @change="loadTasks"
                    />
                </div>
            </template>
        </Card>
        
        <!-- Tasks List -->
        <Card>
            <template #content>
                <DataTable 
                    :value="tasks" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    :rowsPerPageOptions="[10, 25, 50]"
                    responsiveLayout="scroll"
                    dataKey="id"
                    :rowClass="getRowClass"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-inbox" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>No tasks found</p>
                        </div>
                    </template>
                    
                    <Column field="title" header="Task" sortable style="min-width: 250px">
                        <template #body="{ data }">
                            <div class="task-title">
                                <span class="title-en">{{ data.title }}</span>
                                <span class="title-ar" v-if="data.title_ar">{{ data.title_ar }}</span>
                            </div>
                        </template>
                    </Column>
                    
                    <Column field="task_type" header="Type">
                        <template #body="{ data }">
                            <Tag :severity="getTypeSeverity(data.task_type)">
                                {{ formatTaskType(data.task_type) }}
                            </Tag>
                        </template>
                    </Column>
                    
                    <Column field="priority" header="Priority">
                        <template #body="{ data }">
                            <Tag :severity="getPrioritySeverity(data.priority)">
                                {{ data.priority }}
                            </Tag>
                        </template>
                    </Column>
                    
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">
                                {{ data.status }}
                            </Tag>
                        </template>
                    </Column>
                    
                    <Column field="due_date" header="Due Date" sortable>
                        <template #body="{ data }">
                            <div :class="{'overdue-date': isOverdue(data)}">
                                {{ formatDate(data.due_date) }}
                                <i v-if="isOverdue(data)" class="pi pi-exclamation-circle text-danger ml-2"></i>
                            </div>
                        </template>
                    </Column>
                    
                    <Column header="Actions" style="min-width: 180px">
                        <template #body="{ data }">
                            <Button 
                                v-if="data.status === 'pending'"
                                icon="pi pi-play" 
                                label="Start"
                                size="small"
                                class="mr-2"
                                @click="startTask(data)" 
                            />
                            <Button 
                                v-if="data.status === 'in_progress'"
                                icon="pi pi-check" 
                                label="Complete"
                                size="small"
                                severity="success"
                                class="mr-2"
                                @click="openCompleteDialog(data)" 
                            />
                            <Button 
                                icon="pi pi-eye" 
                                text 
                                rounded 
                                @click="viewTask(data)" 
                                v-tooltip="'View Details'"
                            />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>
        
        <!-- Complete Task Dialog -->
        <Dialog 
            v-model:visible="completeDialogVisible" 
            header="Complete Task"
            :style="{ width: '500px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-field">
                    <label>Completion Notes</label>
                    <Textarea v-model="completionNotes" rows="4" placeholder="Enter completion notes..." style="width: 100%" />
                </div>
            </div>
            
            <template #footer>
                <Button label="Cancel" text @click="completeDialogVisible = false" />
                <Button label="Complete Task" icon="pi pi-check" @click="completeTask" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Task Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedTask?.title || 'Task Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedTask">
                <div class="detail-row">
                    <span class="label">Task Type:</span>
                    <Tag :severity="getTypeSeverity(selectedTask.task_type)">{{ formatTaskType(selectedTask.task_type) }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Priority:</span>
                    <Tag :severity="getPrioritySeverity(selectedTask.priority)">{{ selectedTask.priority }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedTask.status)">{{ selectedTask.status }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Due Date:</span>
                    <span class="value">{{ formatDate(selectedTask.due_date) }}</span>
                </div>
                <div class="detail-row" v-if="selectedTask.assigned_by_name">
                    <span class="label">Assigned By:</span>
                    <span class="value">{{ selectedTask.assigned_by_name }}</span>
                </div>
                <div class="detail-row" v-if="selectedTask.description">
                    <span class="label">Description:</span>
                    <span class="value">{{ selectedTask.description }}</span>
                </div>
                <div class="detail-row" v-if="selectedTask.completion_notes">
                    <span class="label">Completion Notes:</span>
                    <span class="value">{{ selectedTask.completion_notes }}</span>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { workflowApi } from '@/api'

const toast = useToast()

const tasks = ref([])
const loading = ref(false)
const saving = ref(false)
const completeDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const selectedTask = ref(null)
const completionNotes = ref('')

const filters = ref({
    search: '',
    status: null,
    priority: null
})

const statusOptions = [
    { label: 'Pending', value: 'pending' },
    { label: 'In Progress', value: 'in_progress' },
    { label: 'Completed', value: 'completed' },
    { label: 'Overdue', value: 'overdue' }
]

const priorityOptions = [
    { label: 'Low', value: 'low' },
    { label: 'Medium', value: 'medium' },
    { label: 'High', value: 'high' },
    { label: 'Critical', value: 'critical' }
]

// Computed counts
const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)
const inProgressCount = computed(() => tasks.value.filter(t => t.status === 'in_progress').length)
const overdueCount = computed(() => tasks.value.filter(t => isOverdue(t)).length)
const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)

const getStatusSeverity = (status) => {
    const map = {
        pending: 'warn',
        in_progress: 'info',
        completed: 'success',
        cancelled: 'secondary',
        overdue: 'danger'
    }
    return map[status] || 'info'
}

const getPrioritySeverity = (priority) => {
    const map = {
        low: 'secondary',
        medium: 'info',
        high: 'warn',
        critical: 'danger'
    }
    return map[priority] || 'info'
}

const getTypeSeverity = (type) => {
    const map = {
        general: 'secondary',
        review: 'info',
        assessment: 'warn',
        evidence: 'success',
        audit: 'danger',
        remediation: 'warn'
    }
    return map[type] || 'info'
}

const formatTaskType = (type) => {
    const map = {
        general: 'General',
        review: 'Review',
        assessment: 'Assessment',
        evidence: 'Evidence',
        audit: 'Audit',
        remediation: 'Remediation'
    }
    return map[type] || type
}

const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

const isOverdue = (task) => {
    if (!task.due_date || task.status === 'completed' || task.status === 'cancelled') return false
    return new Date(task.due_date) < new Date()
}

const getRowClass = (data) => {
    if (isOverdue(data)) return 'overdue-row'
    return null
}

const loadTasks = async () => {
    loading.value = true
    try {
        const response = await workflowApi.tasks.myTasks()
        let allTasks = response.data.results || response.data
        
        // Client-side filtering
        if (filters.value.search) {
            const search = filters.value.search.toLowerCase()
            allTasks = allTasks.filter(t => 
                t.title.toLowerCase().includes(search) ||
                (t.description && t.description.toLowerCase().includes(search))
            )
        }
        if (filters.value.status) {
            allTasks = allTasks.filter(t => t.status === filters.value.status)
        }
        if (filters.value.priority) {
            allTasks = allTasks.filter(t => t.priority === filters.value.priority)
        }
        
        tasks.value = allTasks
    } catch (error) {
        console.error('Failed to load tasks:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load tasks', life: 3000 })
    } finally {
        loading.value = false
    }
}

const startTask = async (task) => {
    try {
        await workflowApi.tasks.start(task.id)
        toast.add({ severity: 'success', summary: 'Success', detail: 'Task started', life: 3000 })
        await loadTasks()
    } catch (error) {
        console.error('Failed to start task:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to start task', life: 3000 })
    }
}

const openCompleteDialog = (task) => {
    selectedTask.value = task
    completionNotes.value = ''
    completeDialogVisible.value = true
}

const completeTask = async () => {
    if (!selectedTask.value) return
    
    saving.value = true
    try {
        await workflowApi.tasks.complete(selectedTask.value.id, completionNotes.value)
        toast.add({ severity: 'success', summary: 'Success', detail: 'Task completed', life: 3000 })
        completeDialogVisible.value = false
        await loadTasks()
    } catch (error) {
        console.error('Failed to complete task:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to complete task', life: 3000 })
    } finally {
        saving.value = false
    }
}

const viewTask = (task) => {
    selectedTask.value = task
    viewDialogVisible.value = true
}

onMounted(() => {
    loadTasks()
})
</script>

<style scoped>
.task-inbox {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
}

.summary-card :deep(.p-card-body) {
    padding: 1rem;
}

.summary-content {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.summary-content i {
    font-size: 2rem;
}

.summary-info {
    display: flex;
    flex-direction: column;
}

.summary-value {
    font-size: 1.5rem;
    font-weight: 700;
}

.summary-label {
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
}

.text-warning { color: var(--p-orange-500); }
.text-info { color: var(--p-blue-500); }
.text-danger { color: var(--p-red-500); }
.text-success { color: var(--p-green-500); }

.filters-card :deep(.p-card-body) {
    padding: 1rem;
}

.filters-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.filter-input,
.filter-dropdown {
    min-width: 200px;
}

.task-title {
    display: flex;
    flex-direction: column;
}

.title-ar {
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
}

.overdue-date {
    color: var(--p-red-500);
    font-weight: 600;
}

.overdue-row {
    background-color: rgba(239, 68, 68, 0.1) !important;
}

.empty-message {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 3rem;
}

.empty-message p {
    color: var(--p-text-muted-color);
    margin: 0;
}

.dialog-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.form-field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.form-field label {
    font-weight: 500;
    font-size: 0.9rem;
}

.view-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.detail-row {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
}

.detail-row .label {
    font-weight: 600;
    min-width: 120px;
    color: var(--p-text-muted-color);
}

.detail-row .value {
    color: var(--p-text-color);
}

.mr-2 {
    margin-right: 0.5rem;
}

.ml-2 {
    margin-left: 0.5rem;
}
</style>
