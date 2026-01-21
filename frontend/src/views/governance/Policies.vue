<template>
    <div class="policies-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('governance.policies') }}</h1>
                <p class="page-subtitle">إدارة السياسات - Policy Management</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <!-- Filters -->
        <Card class="filters-card">
            <template #content>
                <div class="filters-row">
                    <InputText v-model="filters.search" :placeholder="$t('common.search')" class="filter-input" @input="loadPolicies" />
                    <Dropdown 
                        v-model="filters.status" 
                        :options="statusOptions" 
                        optionLabel="label" 
                        optionValue="value"
                        :placeholder="$t('common.status')" 
                        showClear
                        class="filter-dropdown"
                        @change="loadPolicies"
                    />
                </div>
            </template>
        </Card>
        
        <!-- Policies Table -->
        <Card>
            <template #content>
                <DataTable 
                    :value="policies" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    :rowsPerPageOptions="[10, 25, 50]"
                    responsiveLayout="scroll"
                    dataKey="id"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-file" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="policy_id" header="ID" sortable style="min-width: 100px"></Column>
                    <Column field="title" :header="appStore.locale === 'ar' ? 'العنوان' : 'Title'" sortable>
                        <template #body="{ data }">
                            <div class="policy-title">
                                <span class="title-en">{{ data.title }}</span>
                                <span class="title-ar" v-if="data.title_ar">{{ data.title_ar }}</span>
                            </div>
                        </template>
                    </Column>
                    <Column field="status" :header="$t('common.status')">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">
                                {{ data.status }}
                            </Tag>
                        </template>
                    </Column>
                    <Column field="version" header="Version"></Column>
                    <Column field="owner_name" header="Owner"></Column>
                    <Column :header="$t('common.actions')" style="min-width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewPolicy(data)" v-tooltip="$t('common.view')" />
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
            :header="isEdit ? $t('governance.editPolicy') : $t('governance.newPolicy')"
            :style="{ width: '700px' }"
            modal
            class="policy-dialog"
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.id') }} <span class="required">*</span></label>
                        <InputText v-model="form.policy_id" placeholder="POL-001" />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('common.version') }}</label>
                        <InputText v-model="form.version" placeholder="1.0" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.title') }} <span class="required">*</span></label>
                        <InputText v-model="form.title" :placeholder="$t('governance.policyTitlePlaceholder')" />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('common.titleAr') }}</label>
                        <InputText v-model="form.title_ar" placeholder="عنوان السياسة" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.scope') }}</label>
                        <Textarea v-model="form.scope" rows="2" placeholder="Policy scope..." />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('common.scopeAr') }}</label>
                        <Textarea v-model="form.scope_ar" rows="2" placeholder="نطاق السياسة..." dir="rtl" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.status') }}</label>
                        <Dropdown 
                            v-model="form.status" 
                            :options="statusOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            :placeholder="$t('common.selectStatus')"
                        />
                    </div>
                    <div class="form-field">
                        <label>Classification</label>
                        <Dropdown 
                            v-model="form.classification" 
                            :options="classificationOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select classification"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.effectiveDate') }}</label>
                        <Calendar v-model="form.effective_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('common.reviewDate') }}</label>
                        <Calendar v-model="form.review_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                </div>
            </div>
            
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="savePolicy" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedPolicy?.title || 'Policy Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedPolicy">
                <div class="detail-row">
                    <span class="label">Policy ID:</span>
                    <span class="value">{{ selectedPolicy.policy_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Title:</span>
                    <span class="value">{{ selectedPolicy.title }}</span>
                </div>
                <div class="detail-row" v-if="selectedPolicy.title_ar">
                    <span class="label">العنوان:</span>
                    <span class="value">{{ selectedPolicy.title_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedPolicy.status)">{{ selectedPolicy.status }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Purpose:</span>
                    <span class="value">{{ selectedPolicy.purpose }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Scope:</span>
                    <span class="value">{{ selectedPolicy.scope }}</span>
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
import { governanceApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const policies = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedPolicy = ref(null)

const filters = ref({
    search: '',
    status: null
})

const form = ref({
    policy_id: '',
    title: '',
    title_ar: '',
    purpose: '',
    purpose_ar: '',
    scope: '',
    scope_ar: '',
    policy_statement: '',
    policy_statement_ar: '',
    version: '1.0',
    status: 'draft',
    classification: 'internal',
    effective_date: null,
    review_date: null
})

const statusOptions = [
    { label: 'Draft - مسودة', value: 'draft' },
    { label: 'Pending Review - قيد المراجعة', value: 'pending_review' },
    { label: 'Approved - معتمد', value: 'approved' },
    { label: 'Published - منشور', value: 'published' },
    { label: 'Retired - متقاعد', value: 'retired' }
]

const classificationOptions = [
    { label: 'Public - عام', value: 'public' },
    { label: 'Internal - داخلي', value: 'internal' },
    { label: 'Confidential - سري', value: 'confidential' },
    { label: 'Restricted - مقيد', value: 'restricted' }
]

const getStatusSeverity = (status) => {
    const map = {
        draft: 'secondary',
        pending_review: 'warn',
        pending_approval: 'warn',
        approved: 'info',
        published: 'success',
        retired: 'danger'
    }
    return map[status] || 'info'
}

const resetForm = () => {
    form.value = {
        policy_id: '',
        title: '',
        title_ar: '',
        purpose: '',
        purpose_ar: '',
        scope: '',
        scope_ar: '',
        policy_statement: '',
        policy_statement_ar: '',
        version: '1.0',
        status: 'draft',
        classification: 'internal',
        effective_date: null,
        review_date: null
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = (policy) => {
    isEdit.value = true
    selectedPolicy.value = policy
    form.value = { ...policy }
    dialogVisible.value = true
}

const viewPolicy = (policy) => {
    selectedPolicy.value = policy
    viewDialogVisible.value = true
}

const loadPolicies = async () => {
    loading.value = true
    try {
        const params = {
            search: filters.value.search || undefined,
            status: filters.value.status || undefined,
            organization: appStore.currentOrganization?.id
        }
        const response = await governanceApi.policies.list(params)
        policies.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load policies:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load policies', life: 3000 })
    } finally {
        loading.value = false
    }
}

const savePolicy = async () => {
    if (!form.value.policy_id || !form.value.title) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill Policy ID and Title', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/4d636c21-df4c-4da4-9e62-b6bf552d18e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Policies.vue:savePolicy:entry',message:'savePolicy called',data:{formValue:form.value,isEdit:isEdit.value,currentOrgId:appStore.currentOrganization?.id,selectedPolicyId:selectedPolicy.value?.id},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A,B'})}).catch(()=>{});
        // #endregion
        
        // Format dates properly for Django (YYYY-MM-DD)
        const formatDate = (date) => {
            if (!date) return null;
            if (typeof date === 'string') return date;
            if (date instanceof Date) {
                return date.toISOString().split('T')[0];
            }
            return null;
        };
        
        const data = {
            ...form.value,
            organization: appStore.currentOrganization?.id || 1,
            effective_date: formatDate(form.value.effective_date),
            review_date: formatDate(form.value.review_date)
        }
        
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/4d636c21-df4c-4da4-9e62-b6bf552d18e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Policies.vue:savePolicy:beforeRequest',message:'Data prepared for API',data:{preparedData:data,effectiveDateType:typeof form.value.effective_date,reviewDateType:typeof form.value.review_date},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'A,B,D'})}).catch(()=>{});
        // #endregion
        
        if (isEdit.value && selectedPolicy.value?.id) {
            await governanceApi.policies.update(selectedPolicy.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Policy updated successfully', life: 3000 })
        } else {
            await governanceApi.policies.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Policy created successfully', life: 3000 })
        }
        
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/4d636c21-df4c-4da4-9e62-b6bf552d18e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Policies.vue:savePolicy:success',message:'Policy saved successfully',data:{isEdit:isEdit.value},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'SUCCESS'})}).catch(()=>{});
        // #endregion
        
        dialogVisible.value = false
        await loadPolicies()
    } catch (error) {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/4d636c21-df4c-4da4-9e62-b6bf552d18e4',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Policies.vue:savePolicy:error',message:'Save policy failed',data:{errorMessage:error.message,errorStatus:error.response?.status,errorData:error.response?.data,errorConfig:error.config?.data},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'C,D,E'})}).catch(()=>{});
        // #endregion
        console.error('Failed to save policy:', error)
        // Extract user-friendly error message
        let errorMsg = 'Failed to save policy'
        if (error.response?.data) {
            const data = error.response.data
            if (data.non_field_errors?.some(e => e.includes('unique')) || data.policy_id?.some(e => e.includes('unique') || e.includes('exists'))) {
                errorMsg = 'This Policy ID already exists. Please enter a different ID.'
            } else if (data.detail) {
                errorMsg = data.detail
            } else if (data.non_field_errors) {
                errorMsg = data.non_field_errors.join(', ')
            } else {
                const firstKey = Object.keys(data)[0]
                if (firstKey && Array.isArray(data[firstKey])) {
                    errorMsg = `${firstKey}: ${data[firstKey].join(', ')}`
                }
            }
        }
        toast.add({ severity: 'warn', summary: 'Duplicate ID', detail: errorMsg, life: 6000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (policy) => {
    confirm.require({
        message: `Are you sure you want to delete "${policy.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await governanceApi.policies.delete(policy.id)
                await loadPolicies()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Policy deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete policy', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadPolicies()
})
</script>

<style scoped>
.policies-page {
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

.policy-title {
    display: flex;
    flex-direction: column;
}

.title-ar {
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
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
}

.detail-row .label {
    font-weight: 600;
    min-width: 100px;
}

.detail-row .value {
    color: var(--p-text-color);
}
</style>
