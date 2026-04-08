<template>
    <div class="controls-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('compliance.controls') }}</h1>
                <p>{{ appStore.locale === 'ar' ? 'ضوابط الامتثال' : 'Compliance Controls' }}</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <!-- Controls Table -->
        <Card>
            <template #content>
                <DataTable 
                    :value="controls" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-shield" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="control_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Control Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="framework_name" header="Framework"></Column>
                    <Column field="domain_name" header="Domain"></Column>
                    <Column field="control_type" header="Type">
                        <template #body="{ data }">
                            <Tag>{{ data.control_type }}</Tag>
                        </template>
                    </Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewControl(data)" v-tooltip="$t('common.view')" />
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
            :header="isEdit ? 'Edit Control - تعديل الضابط' : 'New Control - ضابط جديد'"
            :style="{ width: '700px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>Control ID <span class="required">*</span></label>
                        <InputText v-model="form.control_id" placeholder="CTRL-001" />
                    </div>
                    <div class="form-field">
                        <label>Framework</label>
                        <Dropdown
                            v-model="selectedFramework"
                            :options="frameworks"
                            optionLabel="name"
                            optionValue="id"
                            placeholder="Select framework"
                            showClear
                            @change="loadDomains"
                        />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Domain</label>
                        <Dropdown
                            v-model="form.domain"
                            :options="domains"
                            optionLabel="name"
                            optionValue="id"
                            placeholder="Select domain"
                            showClear
                        />
                    </div>
                    <div class="form-field">
                        <label>Control Type</label>
                        <Dropdown 
                            v-model="form.control_type" 
                            :options="controlTypeOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select type"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'العنوان' : 'Title' }} <span class="required">*</span></label>
                        <InputText v-model="form.title" placeholder="Control title" />
                    </div>
                    <div class="form-field" v-if="appStore.locale === 'ar'">
                        <label>العنوان (عربي)</label>
                        <InputText v-model="form.title_ar" placeholder="عنوان الضابط" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-field">
                    <label>Description</label>
                    <Textarea v-model="form.description" rows="3" placeholder="Control description..." />
                </div>
                
                <div class="form-field" v-if="appStore.locale === 'ar'">
                    <label>الوصف</label>
                    <Textarea v-model="form.description_ar" rows="3" placeholder="وصف الضابط..." dir="rtl" />
                </div>
                
                <div class="form-field">
                    <label>Evidence Requirements</label>
                    <Textarea v-model="form.evidence_requirements" rows="2" placeholder="Evidence requirements..." />
                </div>
                
                <div class="form-field">
                    <label>متطلبات الأدلة (عربي)</label>
                    <Textarea v-model="form.evidence_requirements_ar" rows="2" placeholder="متطلبات الأدلة..." dir="rtl" />
                </div>
            </div>
            
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveControl" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedControl?.title || 'Control Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedControl">
                <div class="detail-row">
                    <span class="label">Control ID:</span>
                    <span class="value">{{ selectedControl.control_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Title:</span>
                    <span class="value">{{ selectedControl.title }}</span>
                </div>
                <div class="detail-row" v-if="selectedControl.title_ar">
                    <span class="label">العنوان:</span>
                    <span class="value">{{ selectedControl.title_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Type:</span>
                    <Tag>{{ selectedControl.control_type }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Framework:</span>
                    <span class="value">{{ selectedControl.framework_name || '-' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Domain:</span>
                    <span class="value">{{ selectedControl.domain_name || '-' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{{ selectedControl.description }}</span>
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
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { complianceApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const controls = ref([])
const frameworks = ref([])
const domains = ref([])
const selectedFramework = ref(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedControl = ref(null)

const form = ref({
    control_id: '',
    title: '',
    title_ar: '',
    description: '',
    description_ar: '',
    domain: null,
    control_type: 'preventive',
    evidence_requirements: '',
    evidence_requirements_ar: ''
})

const controlTypeOptions = [
    { label: 'Preventive - وقائي', value: 'preventive' },
    { label: 'Detective - كاشف', value: 'detective' },
    { label: 'Corrective - تصحيحي', value: 'corrective' },
    { label: 'Compensating - تعويضي', value: 'compensating' }
]

const resetForm = () => {
    form.value = {
        control_id: '',
        title: '',
        title_ar: '',
        description: '',
        description_ar: '',
        domain: null,
        control_type: 'preventive',
        evidence_requirements: '',
        evidence_requirements_ar: ''
    }
    selectedFramework.value = null
    domains.value = []
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = async (control) => {
    isEdit.value = true
    selectedControl.value = control
    await loadDomains()
    const response = await complianceApi.controls.get(control.id)
    const detail = response.data
    form.value = {
        control_id: detail.control_id || '',
        title: detail.title || '',
        title_ar: detail.title_ar || '',
        description: detail.description || '',
        description_ar: detail.description_ar || '',
        domain: detail.domain || null,
        control_type: detail.control_type || 'preventive',
        evidence_requirements: detail.evidence_requirements || '',
        evidence_requirements_ar: detail.evidence_requirements_ar || ''
    }
    const selectedDomain = domains.value.find((item) => item.id === detail.domain)
    selectedFramework.value = selectedDomain?.framework || null
    if (selectedFramework.value) {
        await loadDomains()
    }
    dialogVisible.value = true
}

const viewControl = (control) => {
    selectedControl.value = control
    viewDialogVisible.value = true
}

const loadControls = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await complianceApi.controls.list({ organization: orgId })
        controls.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load controls:', error)
    } finally {
        loading.value = false
    }
}

const loadFrameworks = async () => {
    try {
        const response = await complianceApi.frameworks.list()
        frameworks.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load frameworks:', error)
    }
}

const loadDomains = async () => {
    try {
        const params = selectedFramework.value ? { framework: selectedFramework.value } : {}
        const response = await complianceApi.domains.list(params)
        domains.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load domains:', error)
    }
}

const saveControl = async () => {
    if (!form.value.control_id || !form.value.title) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill Control ID and Title', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        const data = {
            control_id: form.value.control_id,
            title: form.value.title,
            title_ar: form.value.title_ar,
            description: form.value.description,
            description_ar: form.value.description_ar,
            domain: form.value.domain,
            control_type: form.value.control_type,
            evidence_requirements: form.value.evidence_requirements,
            evidence_requirements_ar: form.value.evidence_requirements_ar
        }
        
        if (isEdit.value && selectedControl.value?.id) {
            await complianceApi.controls.update(selectedControl.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Control updated successfully', life: 3000 })
        } else {
            await complianceApi.controls.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Control created successfully', life: 3000 })
        }
        
        dialogVisible.value = false
        await loadControls()
    } catch (error) {
        console.error('Failed to save control:', error)
        // Extract user-friendly error message
        let errorMsg = 'Failed to save control'
        if (error.response?.data) {
            const data = error.response.data
            if (data.non_field_errors?.some(e => e.includes('unique')) || data.control_id?.some(e => e.includes('unique') || e.includes('exists'))) {
                errorMsg = 'This Control ID already exists. Please enter a different ID.'
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

const confirmDelete = (control) => {
    confirm.require({
        message: `Are you sure you want to delete "${control.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await complianceApi.controls.delete(control.id)
                await loadControls()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Control deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete control', life: 3000 })
            }
        }
    })
}

onMounted(async () => {
    await Promise.all([loadControls(), loadFrameworks()])
})
</script>

<style scoped>
.controls-page {
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
