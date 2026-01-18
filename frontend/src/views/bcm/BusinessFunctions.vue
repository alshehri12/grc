<template>
    <div class="bcm-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('bcm.functions') }}</h1>
                <p>وظائف الأعمال - Business Functions</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <!-- Functions Table -->
        <Card>
            <template #content>
                <DataTable 
                    :value="functions" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-sitemap" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="function_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="name" header="Function Name">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.name }}</span>
                                <div class="text-muted" v-if="data.name_ar">{{ data.name_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="criticality" header="Criticality">
                        <template #body="{ data }">
                            <Tag :severity="getCriticalitySeverity(data.criticality)">
                                {{ getCriticalityLabel(data.criticality) }}
                            </Tag>
                        </template>
                    </Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="data.status === 'active' ? 'success' : 'secondary'">
                                {{ data.status }}
                            </Tag>
                        </template>
                    </Column>
                    <Column field="department_name" header="Department"></Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewFunction(data)" v-tooltip="$t('common.view')" />
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
            :header="isEdit ? 'Edit Business Function - تعديل وظيفة الأعمال' : 'New Business Function - وظيفة أعمال جديدة'"
            :style="{ width: '700px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>Function ID <span class="required">*</span></label>
                        <InputText v-model="form.function_id" placeholder="BF-001" />
                    </div>
                    <div class="form-field">
                        <label>Criticality <span class="required">*</span></label>
                        <Dropdown 
                            v-model="form.criticality" 
                            :options="criticalityOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select criticality"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Name (English) <span class="required">*</span></label>
                        <InputText v-model="form.name" placeholder="Function name" />
                    </div>
                    <div class="form-field">
                        <label>الاسم (عربي)</label>
                        <InputText v-model="form.name_ar" placeholder="اسم الوظيفة" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-field">
                    <label>Description <span class="required">*</span></label>
                    <Textarea v-model="form.description" rows="3" placeholder="Function description..." />
                </div>
                
                <div class="form-field">
                    <label>الوصف (عربي)</label>
                    <Textarea v-model="form.description_ar" rows="3" placeholder="وصف الوظيفة..." dir="rtl" />
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
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveFunction" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedFunction?.name || 'Function Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedFunction">
                <div class="detail-row">
                    <span class="label">Function ID:</span>
                    <span class="value">{{ selectedFunction.function_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Name:</span>
                    <span class="value">{{ selectedFunction.name }}</span>
                </div>
                <div class="detail-row" v-if="selectedFunction.name_ar">
                    <span class="label">الاسم:</span>
                    <span class="value">{{ selectedFunction.name_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Criticality:</span>
                    <Tag :severity="getCriticalitySeverity(selectedFunction.criticality)">
                        {{ getCriticalityLabel(selectedFunction.criticality) }}
                    </Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{{ selectedFunction.description }}</span>
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
import { bcmApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const functions = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedFunction = ref(null)

const form = ref({
    function_id: '',
    name: '',
    name_ar: '',
    description: '',
    description_ar: '',
    criticality: 'necessary',
    status: 'active'
})

const criticalityOptions = [
    { label: 'Critical - حرج', value: 'critical' },
    { label: 'Essential - أساسي', value: 'essential' },
    { label: 'Necessary - ضروري', value: 'necessary' },
    { label: 'Desirable - مرغوب', value: 'desirable' }
]

const statusOptions = [
    { label: 'Active - نشط', value: 'active' },
    { label: 'Inactive - غير نشط', value: 'inactive' },
    { label: 'Under Review - قيد المراجعة', value: 'under_review' }
]

const getCriticalitySeverity = (criticality) => {
    const map = {
        critical: 'danger',
        essential: 'warn',
        necessary: 'info',
        desirable: 'success'
    }
    return map[criticality] || 'info'
}

const getCriticalityLabel = (criticality) => {
    const map = {
        critical: 'Critical - حرج',
        essential: 'Essential - أساسي',
        necessary: 'Necessary - ضروري',
        desirable: 'Desirable - مرغوب'
    }
    return map[criticality] || criticality
}

const resetForm = () => {
    form.value = {
        function_id: '',
        name: '',
        name_ar: '',
        description: '',
        description_ar: '',
        criticality: 'necessary',
        status: 'active'
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = (func) => {
    isEdit.value = true
    selectedFunction.value = func
    form.value = { ...func }
    dialogVisible.value = true
}

const viewFunction = (func) => {
    selectedFunction.value = func
    viewDialogVisible.value = true
}

const loadFunctions = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await bcmApi.functions.list({ organization: orgId })
        functions.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load functions:', error)
    } finally {
        loading.value = false
    }
}

const saveFunction = async () => {
    if (!form.value.function_id || !form.value.name) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill Function ID and Name', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        const data = {
            ...form.value,
            organization: appStore.currentOrganization?.id || 1
        }
        
        if (isEdit.value && selectedFunction.value?.id) {
            await bcmApi.functions.update(selectedFunction.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Function updated successfully', life: 3000 })
        } else {
            await bcmApi.functions.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Function created successfully', life: 3000 })
        }
        
        dialogVisible.value = false
        await loadFunctions()
    } catch (error) {
        console.error('Failed to save function:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: error.response?.data?.detail || 'Failed to save function', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (func) => {
    confirm.require({
        message: `Are you sure you want to delete "${func.name}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await bcmApi.functions.delete(func.id)
                await loadFunctions()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Function deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete function', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadFunctions()
})
</script>

<style scoped>
.bcm-page {
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
