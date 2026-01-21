<template>
    <div class="approval-center">
        <div class="page-header">
            <div>
                <h1>{{ $t('workflow.approvalCenter') || 'Approval Center' }}</h1>
                <p class="page-subtitle">مركز الاعتمادات - Manage pending approvals</p>
            </div>
        </div>
        
        <!-- Summary Cards -->
        <div class="summary-cards">
            <Card class="summary-card pending">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-clock"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ pendingCount }}</span>
                            <span class="summary-label">Pending Approvals</span>
                        </div>
                    </div>
                </template>
            </Card>
            <Card class="summary-card overdue">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-exclamation-triangle"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ overdueCount }}</span>
                            <span class="summary-label">Overdue</span>
                        </div>
                    </div>
                </template>
            </Card>
            <Card class="summary-card approved">
                <template #content>
                    <div class="summary-content">
                        <i class="pi pi-check-circle"></i>
                        <div class="summary-info">
                            <span class="summary-value">{{ approvedTodayCount }}</span>
                            <span class="summary-label">Approved Today</span>
                        </div>
                    </div>
                </template>
            </Card>
        </div>
        
        <!-- Pending Approvals Table -->
        <Card>
            <template #title>
                <div class="card-title-row">
                    <span>Pending Approvals</span>
                    <Button icon="pi pi-refresh" text rounded @click="loadApprovals" :loading="loading" />
                </div>
            </template>
            <template #content>
                <DataTable 
                    :value="approvals" 
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
                            <i class="pi pi-check-circle" style="font-size: 3rem; color: var(--p-green-500);"></i>
                            <p>All caught up! No pending approvals.</p>
                        </div>
                    </template>
                    
                    <Column field="workflow_title" header="Item" sortable style="min-width: 250px">
                        <template #body="{ data }">
                            <div class="item-info">
                                <span class="item-title">{{ data.workflow_title }}</span>
                                <span class="workflow-name">{{ data.workflow_instance?.template_name }}</span>
                            </div>
                        </template>
                    </Column>
                    
                    <Column field="step_name" header="Step">
                        <template #body="{ data }">
                            <Tag severity="info">{{ data.step_name }}</Tag>
                        </template>
                    </Column>
                    
                    <Column header="Submitted By" style="min-width: 150px">
                        <template #body="{ data }">
                            <div class="submitter-info">
                                <span class="submitter-name">{{ data.workflow_instance?.initiated_by_name || 'N/A' }}</span>
                                <span class="submitter-dept" v-if="data.workflow_instance?.initiated_by_department">
                                    {{ data.workflow_instance.initiated_by_department.name }}
                                </span>
                            </div>
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
                    
                    <Column field="created_at" header="Requested" sortable>
                        <template #body="{ data }">
                            {{ formatDate(data.created_at) }}
                        </template>
                    </Column>
                    
                    <Column header="Actions" style="min-width: 220px">
                        <template #body="{ data }">
                            <Button 
                                icon="pi pi-check" 
                                label="Approve"
                                size="small"
                                severity="success"
                                class="mr-2"
                                @click="openApproveDialog(data)" 
                            />
                            <Button 
                                icon="pi pi-times" 
                                label="Reject"
                                size="small"
                                severity="danger"
                                class="mr-2"
                                @click="openRejectDialog(data)" 
                            />
                            <Button 
                                icon="pi pi-eye" 
                                text 
                                rounded 
                                @click="viewApproval(data)" 
                                v-tooltip="'View Details'"
                            />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>
        
        <!-- Approve Dialog -->
        <Dialog 
            v-model:visible="approveDialogVisible" 
            header="Approve Request"
            :style="{ width: '500px' }"
            modal
        >
            <div class="dialog-content" v-if="selectedApproval">
                <div class="approval-summary">
                    <p><strong>Item:</strong> {{ selectedApproval.workflow_title }}</p>
                    <p><strong>Step:</strong> {{ selectedApproval.step_name }}</p>
                </div>
                <div class="form-field">
                    <label>Comments (Optional)</label>
                    <Textarea v-model="approvalComments" rows="3" placeholder="Enter approval comments..." style="width: 100%" />
                </div>
            </div>
            
            <template #footer>
                <Button label="Cancel" text @click="approveDialogVisible = false" />
                <Button label="Approve" icon="pi pi-check" severity="success" @click="approveRequest" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- Reject Dialog -->
        <Dialog 
            v-model:visible="rejectDialogVisible" 
            header="Reject Request"
            :style="{ width: '500px' }"
            modal
        >
            <div class="dialog-content" v-if="selectedApproval">
                <div class="approval-summary">
                    <p><strong>Item:</strong> {{ selectedApproval.workflow_title }}</p>
                    <p><strong>Step:</strong> {{ selectedApproval.step_name }}</p>
                </div>
                <div class="form-field">
                    <label>Reason for Rejection <span class="required">*</span></label>
                    <Textarea v-model="rejectionReason" rows="3" placeholder="Please provide a reason for rejection..." style="width: 100%" />
                </div>
            </div>
            
            <template #footer>
                <Button label="Cancel" text @click="rejectDialogVisible = false" />
                <Button label="Reject" icon="pi pi-times" severity="danger" @click="rejectRequest" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Details Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedApproval?.workflow_title || 'Approval Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedApproval">
                <div class="detail-row">
                    <span class="label">Workflow:</span>
                    <span class="value">{{ selectedApproval.workflow_instance?.template_name }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Item:</span>
                    <span class="value">{{ selectedApproval.workflow_title }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Step:</span>
                    <Tag severity="info">{{ selectedApproval.step_name }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedApproval.status)">{{ selectedApproval.status }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Due Date:</span>
                    <span class="value" :class="{'overdue-date': isOverdue(selectedApproval)}">
                        {{ formatDate(selectedApproval.due_date) }}
                    </span>
                </div>
                <div class="detail-row">
                    <span class="label">Requested At:</span>
                    <span class="value">{{ formatDate(selectedApproval.created_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedApproval.assignee_name">
                    <span class="label">Assignee:</span>
                    <span class="value">{{ selectedApproval.assignee_name }}</span>
                </div>
                
                <!-- Step Instructions -->
                <div class="instructions-section" v-if="selectedApproval.step?.instructions">
                    <h4>Instructions</h4>
                    <p>{{ selectedApproval.step.instructions }}</p>
                </div>
            </div>
            
            <template #footer>
                <Button label="Close" text @click="viewDialogVisible = false" />
                <Button 
                    v-if="selectedApproval?.status === 'pending'"
                    label="Approve" 
                    icon="pi pi-check" 
                    severity="success" 
                    class="mr-2"
                    @click="viewDialogVisible = false; openApproveDialog(selectedApproval)" 
                />
                <Button 
                    v-if="selectedApproval?.status === 'pending'"
                    label="Reject" 
                    icon="pi pi-times" 
                    severity="danger" 
                    @click="viewDialogVisible = false; openRejectDialog(selectedApproval)" 
                />
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { workflowApi } from '@/api'

const toast = useToast()

const approvals = ref([])
const loading = ref(false)
const saving = ref(false)
const approveDialogVisible = ref(false)
const rejectDialogVisible = ref(false)
const viewDialogVisible = ref(false)
const selectedApproval = ref(null)
const approvalComments = ref('')
const rejectionReason = ref('')

// Computed counts
const pendingCount = computed(() => approvals.value.length)
const overdueCount = computed(() => approvals.value.filter(a => isOverdue(a)).length)
const approvedTodayCount = ref(0) // Would need separate API call

const getStatusSeverity = (status) => {
    const map = {
        pending: 'warn',
        approved: 'success',
        rejected: 'danger',
        delegated: 'info'
    }
    return map[status] || 'info'
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

const isOverdue = (approval) => {
    if (!approval.due_date || approval.status !== 'pending') return false
    return new Date(approval.due_date) < new Date()
}

const getRowClass = (data) => {
    if (isOverdue(data)) return 'overdue-row'
    return null
}

const loadApprovals = async () => {
    loading.value = true
    try {
        const response = await workflowApi.approvals.myPending()
        approvals.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load approvals:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load approvals', life: 3000 })
    } finally {
        loading.value = false
    }
}

const openApproveDialog = (approval) => {
    selectedApproval.value = approval
    approvalComments.value = ''
    approveDialogVisible.value = true
}

const openRejectDialog = (approval) => {
    selectedApproval.value = approval
    rejectionReason.value = ''
    rejectDialogVisible.value = true
}

const viewApproval = (approval) => {
    selectedApproval.value = approval
    viewDialogVisible.value = true
}

const approveRequest = async () => {
    if (!selectedApproval.value) return
    
    saving.value = true
    try {
        await workflowApi.approvals.approve(selectedApproval.value.id, approvalComments.value)
        toast.add({ severity: 'success', summary: 'Approved', detail: 'Request has been approved', life: 3000 })
        approveDialogVisible.value = false
        await loadApprovals()
    } catch (error) {
        console.error('Failed to approve:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to approve request', life: 3000 })
    } finally {
        saving.value = false
    }
}

const rejectRequest = async () => {
    if (!selectedApproval.value) return
    
    if (!rejectionReason.value.trim()) {
        toast.add({ severity: 'warn', summary: 'Required', detail: 'Please provide a reason for rejection', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        await workflowApi.approvals.reject(selectedApproval.value.id, rejectionReason.value)
        toast.add({ severity: 'info', summary: 'Rejected', detail: 'Request has been rejected', life: 3000 })
        rejectDialogVisible.value = false
        await loadApprovals()
    } catch (error) {
        console.error('Failed to reject:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to reject request', life: 3000 })
    } finally {
        saving.value = false
    }
}

onMounted(() => {
    loadApprovals()
})
</script>

<style scoped>
.approval-center {
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
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
}

.summary-card :deep(.p-card-body) {
    padding: 1.25rem;
}

.summary-card.pending {
    border-left: 4px solid var(--p-orange-500);
}

.summary-card.overdue {
    border-left: 4px solid var(--p-red-500);
}

.summary-card.approved {
    border-left: 4px solid var(--p-green-500);
}

.summary-content {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.summary-content i {
    font-size: 2.5rem;
}

.summary-card.pending i { color: var(--p-orange-500); }
.summary-card.overdue i { color: var(--p-red-500); }
.summary-card.approved i { color: var(--p-green-500); }

.summary-info {
    display: flex;
    flex-direction: column;
}

.summary-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}

.summary-label {
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
    margin-top: 0.25rem;
}

.card-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.item-info {
    display: flex;
    flex-direction: column;
}

.item-title {
    font-weight: 500;
}

.workflow-name {
    font-size: 0.8rem;
    color: var(--p-text-muted-color);
}

.submitter-info {
    display: flex;
    flex-direction: column;
}

.submitter-name {
    font-weight: 500;
}

.submitter-dept {
    font-size: 0.8rem;
    color: var(--p-text-muted-color);
}

.overdue-date {
    color: var(--p-red-500);
    font-weight: 600;
}

.text-danger {
    color: var(--p-red-500);
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

.approval-summary {
    background: var(--p-surface-100);
    padding: 1rem;
    border-radius: 8px;
}

.approval-summary p {
    margin: 0.25rem 0;
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

.form-field .required {
    color: var(--p-red-500);
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

.instructions-section {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--p-surface-100);
    border-radius: 8px;
}

.instructions-section h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
}

.instructions-section p {
    margin: 0;
    white-space: pre-wrap;
}

.mr-2 {
    margin-right: 0.5rem;
}

.ml-2 {
    margin-left: 0.5rem;
}
</style>
