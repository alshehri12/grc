<template>
    <div class="audits-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('compliance.audits') }}</h1>
                <p>التدقيق والمراجعة - Audits</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <!-- Audits Table -->
        <Card>
            <template #content>
                <DataTable 
                    :value="audits" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-search" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="audit_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Audit Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="audit_type" header="Type">
                        <template #body="{ data }">
                            <Tag>{{ data.audit_type }}</Tag>
                        </template>
                    </Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column field="scheduled_start" header="Start Date"></Column>
                    <Column field="lead_auditor_name" header="Lead Auditor"></Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewAudit(data)" v-tooltip="$t('common.view')" />
                            <Button icon="pi pi-pencil" text rounded @click="openEditDialog(data)" v-tooltip="$t('common.edit')" />
                            <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" v-tooltip="$t('common.delete')" />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>
        
        <!-- Create/Edit Dialog -->
        <Dialog 
            v-model:visible="dialogVisible" 
            :header="isEdit ? 'Edit Audit - تعديل التدقيق' : 'New Audit - تدقيق جديد'"
            :style="{ width: '700px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>Audit ID <span class="required">*</span></label>
                        <InputText v-model="form.audit_id" placeholder="AUD-001" />
                    </div>
                    <div class="form-field">
                        <label>Audit Type</label>
                        <Dropdown 
                            v-model="form.audit_type" 
                            :options="auditTypeOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select type"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Title (English) <span class="required">*</span></label>
                        <InputText v-model="form.title" placeholder="Audit title" />
                    </div>
                    <div class="form-field">
                        <label>العنوان (عربي)</label>
                        <InputText v-model="form.title_ar" placeholder="عنوان التدقيق" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-field">
                    <label>Objectives <span class="required">*</span></label>
                    <Textarea v-model="form.objectives" rows="3" placeholder="Audit objectives..." />
                </div>
                
                <div class="form-field">
                    <label>الأهداف (عربي)</label>
                    <Textarea v-model="form.objectives_ar" rows="3" placeholder="أهداف التدقيق..." dir="rtl" />
                </div>
                
                <div class="form-field">
                    <label>Scope <span class="required">*</span></label>
                    <Textarea v-model="form.scope" rows="2" placeholder="Audit scope..." />
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Scheduled Start</label>
                        <Calendar v-model="form.scheduled_start" dateFormat="yy-mm-dd" showIcon />
                    </div>
                    <div class="form-field">
                        <label>Scheduled End</label>
                        <Calendar v-model="form.scheduled_end" dateFormat="yy-mm-dd" showIcon />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Status</label>
                        <Dropdown 
                            v-model="form.status" 
                            :options="statusOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select status"
                        />
                    </div>
                </div>
            </div>
            
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveAudit" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedAudit?.title || 'Audit Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedAudit">
                <div class="detail-row">
                    <span class="label">Audit ID:</span>
                    <span class="value">{{ selectedAudit.audit_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Title:</span>
                    <span class="value">{{ selectedAudit.title }}</span>
                </div>
                <div class="detail-row" v-if="selectedAudit.title_ar">
                    <span class="label">العنوان:</span>
                    <span class="value">{{ selectedAudit.title_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Type:</span>
                    <Tag>{{ selectedAudit.audit_type }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedAudit.status)">{{ selectedAudit.status }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Objectives:</span>
                    <span class="value">{{ selectedAudit.objectives }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Scope:</span>
                    <span class="value">{{ selectedAudit.scope }}</span>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { complianceApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const audits = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedAudit = ref(null)

const form = ref({
    audit_id: '',
    title: '',
    title_ar: '',
    objectives: '',
    objectives_ar: '',
    scope: '',
    audit_type: 'internal',
    status: 'planned',
    scheduled_start: null,
    scheduled_end: null
})

const auditTypeOptions = [
    { label: 'Internal - داخلي', value: 'internal' },
    { label: 'External - خارجي', value: 'external' },
    { label: 'Certification - شهادة', value: 'certification' },
    { label: 'Regulatory - تنظيمي', value: 'regulatory' }
]

const statusOptions = [
    { label: 'Planned - مخطط', value: 'planned' },
    { label: 'In Progress - قيد التنفيذ', value: 'in_progress' },
    { label: 'Completed - مكتمل', value: 'completed' },
    { label: 'Cancelled - ملغي', value: 'cancelled' }
]

const getStatusSeverity = (status) => {
    const map = {
        planned: 'info',
        in_progress: 'warn',
        completed: 'success',
        cancelled: 'secondary'
    }
    return map[status] || 'info'
}

const resetForm = () => {
    form.value = {
        audit_id: '',
        title: '',
        title_ar: '',
        objectives: '',
        objectives_ar: '',
        scope: '',
        audit_type: 'internal',
        status: 'planned',
        scheduled_start: null,
        scheduled_end: null
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = (audit) => {
    isEdit.value = true
    selectedAudit.value = audit
    form.value = { ...audit }
    dialogVisible.value = true
}

const viewAudit = (audit) => {
    selectedAudit.value = audit
    viewDialogVisible.value = true
}

const loadAudits = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await complianceApi.audits.list({ organization: orgId })
        audits.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load audits:', error)
    } finally {
        loading.value = false
    }
}

const saveAudit = async () => {
    if (!form.value.audit_id || !form.value.title || !form.value.objectives || !form.value.scope) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill all required fields', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        const data = {
            ...form.value,
            organization: appStore.currentOrganization?.id || 1
        }
        
        if (isEdit.value && selectedAudit.value?.id) {
            await complianceApi.audits.update(selectedAudit.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Audit updated successfully', life: 3000 })
        } else {
            await complianceApi.audits.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Audit created successfully', life: 3000 })
        }
        
        dialogVisible.value = false
        await loadAudits()
    } catch (error) {
        console.error('Failed to save audit:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail || 'Failed to save audit', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (audit) => {
    confirm.require({
        message: `Are you sure you want to delete "${audit.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await complianceApi.audits.delete(audit.id)
                await loadAudits()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Audit deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete audit', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadAudits()
})
</script>

<style scoped>
.audits-page {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.page-header h1 { margin: 0; }
.page-header p { margin: 0.25rem 0 0; color: var(--p-text-muted-color); }

.text-muted { font-size: 0.85rem; color: var(--p-text-muted-color); }

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

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
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

.form-field .required {
    color: var(--p-red-500);
}

.form-field :deep(.p-inputtext),
.form-field :deep(.p-dropdown),
.form-field :deep(.p-calendar),
.form-field :deep(.p-inputtextarea) {
    width: 100%;
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
    min-width: 100px;
}
</style>
