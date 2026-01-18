<template>
    <div class="bcm-plans-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('bcm.plans') }}</h1>
                <p>خطط استمرارية الأعمال - Business Continuity Plans</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <!-- Plans Table -->
        <Card>
            <template #content>
                <DataTable 
                    :value="plans" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-book" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="plan_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="name" header="Plan Name">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.name }}</span>
                                <div class="text-muted" v-if="data.name_ar">{{ data.name_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="plan_type" header="Type">
                        <template #body="{ data }">
                            <Tag>{{ getPlanTypeLabel(data.plan_type) }}</Tag>
                        </template>
                    </Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column field="version" header="Version"></Column>
                    <Column field="last_test_date" header="Last Test"></Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewPlan(data)" v-tooltip="$t('common.view')" />
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
            :header="isEdit ? 'Edit BC Plan - تعديل خطة استمرارية الأعمال' : 'New BC Plan - خطة استمرارية أعمال جديدة'"
            :style="{ width: '750px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>Plan ID <span class="required">*</span></label>
                        <InputText v-model="form.plan_id" placeholder="BCP-001" />
                    </div>
                    <div class="form-field">
                        <label>Plan Type <span class="required">*</span></label>
                        <Dropdown 
                            v-model="form.plan_type" 
                            :options="planTypeOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select type"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Name (English) <span class="required">*</span></label>
                        <InputText v-model="form.name" placeholder="Plan name" />
                    </div>
                    <div class="form-field">
                        <label>الاسم (عربي)</label>
                        <InputText v-model="form.name_ar" placeholder="اسم الخطة" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-field">
                    <label>Description <span class="required">*</span></label>
                    <Textarea v-model="form.description" rows="3" placeholder="Plan description..." />
                </div>
                
                <div class="form-field">
                    <label>الوصف (عربي)</label>
                    <Textarea v-model="form.description_ar" rows="3" placeholder="وصف الخطة..." dir="rtl" />
                </div>
                
                <div class="form-field">
                    <label>Scope <span class="required">*</span></label>
                    <Textarea v-model="form.scope" rows="2" placeholder="Plan scope..." />
                </div>
                
                <div class="form-field">
                    <label>Objectives</label>
                    <Textarea v-model="form.objectives" rows="2" placeholder="Plan objectives..." />
                </div>
                
                <Divider />
                
                <h4>Recovery Targets - أهداف الاسترداد</h4>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>RTO (Recovery Time Objective)</label>
                        <InputText v-model="form.rto" placeholder="e.g., 4 hours" />
                    </div>
                    <div class="form-field">
                        <label>RPO (Recovery Point Objective)</label>
                        <InputText v-model="form.rpo" placeholder="e.g., 1 hour" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Version</label>
                        <InputText v-model="form.version" placeholder="1.0" />
                    </div>
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
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Review Date</label>
                        <Calendar v-model="form.review_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                    <div class="form-field">
                        <label>Expiry Date</label>
                        <Calendar v-model="form.expiry_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                </div>
            </div>
            
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="savePlan" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedPlan?.name || 'Plan Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedPlan">
                <div class="detail-row">
                    <span class="label">Plan ID:</span>
                    <span class="value">{{ selectedPlan.plan_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Name:</span>
                    <span class="value">{{ selectedPlan.name }}</span>
                </div>
                <div class="detail-row" v-if="selectedPlan.name_ar">
                    <span class="label">الاسم:</span>
                    <span class="value">{{ selectedPlan.name_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Type:</span>
                    <Tag>{{ getPlanTypeLabel(selectedPlan.plan_type) }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedPlan.status)">{{ selectedPlan.status }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">RTO:</span>
                    <span class="value">{{ selectedPlan.rto || 'Not set' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">RPO:</span>
                    <span class="value">{{ selectedPlan.rpo || 'Not set' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{{ selectedPlan.description }}</span>
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
import Divider from 'primevue/divider'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { bcmApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const plans = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedPlan = ref(null)

const form = ref({
    plan_id: '',
    name: '',
    name_ar: '',
    description: '',
    description_ar: '',
    scope: '',
    objectives: '',
    plan_type: 'bcp',
    status: 'draft',
    version: '1.0',
    rto: '',
    rpo: '',
    review_date: null,
    expiry_date: null
})

const planTypeOptions = [
    { label: 'BCP - خطة استمرارية الأعمال', value: 'bcp' },
    { label: 'DRP - خطة التعافي من الكوارث', value: 'drp' },
    { label: 'IRP - خطة الاستجابة للحوادث', value: 'irp' },
    { label: 'CMP - خطة إدارة الأزمات', value: 'cmp' }
]

const statusOptions = [
    { label: 'Draft - مسودة', value: 'draft' },
    { label: 'Under Review - قيد المراجعة', value: 'under_review' },
    { label: 'Approved - معتمد', value: 'approved' },
    { label: 'Active - نشط', value: 'active' },
    { label: 'Expired - منتهي', value: 'expired' }
]

const getPlanTypeLabel = (type) => {
    const map = {
        bcp: 'BCP',
        drp: 'DRP',
        irp: 'IRP',
        cmp: 'CMP'
    }
    return map[type] || type
}

const getStatusSeverity = (status) => {
    const map = {
        draft: 'secondary',
        under_review: 'warn',
        approved: 'info',
        active: 'success',
        expired: 'danger'
    }
    return map[status] || 'info'
}

const resetForm = () => {
    form.value = {
        plan_id: '',
        name: '',
        name_ar: '',
        description: '',
        description_ar: '',
        scope: '',
        objectives: '',
        plan_type: 'bcp',
        status: 'draft',
        version: '1.0',
        rto: '',
        rpo: '',
        review_date: null,
        expiry_date: null
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = (plan) => {
    isEdit.value = true
    selectedPlan.value = plan
    form.value = { ...plan }
    dialogVisible.value = true
}

const viewPlan = (plan) => {
    selectedPlan.value = plan
    viewDialogVisible.value = true
}

const loadPlans = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await bcmApi.plans.list({ organization: orgId })
        plans.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load plans:', error)
    } finally {
        loading.value = false
    }
}

const savePlan = async () => {
    if (!form.value.plan_id || !form.value.name || !form.value.description || !form.value.scope) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill all required fields', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        const data = {
            ...form.value,
            organization: appStore.currentOrganization?.id || 1
        }
        
        if (isEdit.value && selectedPlan.value?.id) {
            await bcmApi.plans.update(selectedPlan.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Plan updated successfully', life: 3000 })
        } else {
            await bcmApi.plans.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Plan created successfully', life: 3000 })
        }
        
        dialogVisible.value = false
        await loadPlans()
    } catch (error) {
        console.error('Failed to save plan:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail || 'Failed to save plan', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (plan) => {
    confirm.require({
        message: `Are you sure you want to delete "${plan.name}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await bcmApi.plans.delete(plan.id)
                await loadPlans()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Plan deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete plan', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadPlans()
})
</script>

<style scoped>
.bcm-plans-page {
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

.dialog-content h4 {
    margin: 0;
    color: var(--p-primary-color);
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
