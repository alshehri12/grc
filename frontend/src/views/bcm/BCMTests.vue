<template>
    <div class="bcm-tests-page">
        <div class="page-header">
            <div>
                <h1>BCM Tests & Exercises</h1>
                <p>اختبارات وتمارين استمرارية الأعمال</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <Card>
            <template #content>
                <DataTable 
                    :value="tests" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-check-circle" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="test_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Test Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="test_type" header="Type">
                        <template #body="{ data }">
                            <Tag>{{ getTestTypeLabel(data.test_type) }}</Tag>
                        </template>
                    </Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column field="scheduled_date" header="Scheduled Date"></Column>
                    <Column field="overall_result" header="Result">
                        <template #body="{ data }">
                            <Tag v-if="data.overall_result" :severity="getResultSeverity(data.overall_result)">
                                {{ data.overall_result }}
                            </Tag>
                            <span v-else>-</span>
                        </template>
                    </Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewTest(data)" v-tooltip="$t('common.view')" />
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
            :header="isEdit ? 'Edit BCM Test - تعديل اختبار استمرارية الأعمال' : 'New BCM Test - اختبار استمرارية أعمال جديد'"
            :style="{ width: '700px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>Test ID <span class="required">*</span></label>
                        <InputText v-model="form.test_id" placeholder="TST-001" />
                    </div>
                    <div class="form-field">
                        <label>Test Type <span class="required">*</span></label>
                        <Dropdown 
                            v-model="form.test_type" 
                            :options="testTypeOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select type"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Title (English) <span class="required">*</span></label>
                        <InputText v-model="form.title" placeholder="Test title" />
                    </div>
                    <div class="form-field">
                        <label>العنوان (عربي)</label>
                        <InputText v-model="form.title_ar" placeholder="عنوان الاختبار" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-field">
                    <label>Objectives <span class="required">*</span></label>
                    <Textarea v-model="form.objectives" rows="3" placeholder="Test objectives..." />
                </div>
                
                <div class="form-field">
                    <label>الأهداف (عربي)</label>
                    <Textarea v-model="form.objectives_ar" rows="3" placeholder="أهداف الاختبار..." dir="rtl" />
                </div>
                
                <div class="form-field">
                    <label>Scope <span class="required">*</span></label>
                    <Textarea v-model="form.scope" rows="2" placeholder="Test scope..." />
                </div>
                
                <div class="form-field">
                    <label>Test Scenario <span class="required">*</span></label>
                    <Textarea v-model="form.scenario" rows="3" placeholder="Describe the test scenario..." />
                </div>
                
                <div class="form-field">
                    <label>سيناريو الاختبار (عربي)</label>
                    <Textarea v-model="form.scenario_ar" rows="3" placeholder="وصف سيناريو الاختبار..." dir="rtl" />
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>Scheduled Date <span class="required">*</span></label>
                        <Calendar v-model="form.scheduled_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                    <div class="form-field">
                        <label>Status</label>
                        <Dropdown 
                            v-model="form.status" 
                            :options="statusOptions" 
                            optionLabel="label" 
                            optionValue="value"
                        />
                    </div>
                </div>
            </div>
            
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveTest" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedTest?.title || 'Test Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedTest">
                <div class="detail-row">
                    <span class="label">Test ID:</span>
                    <span class="value">{{ selectedTest.test_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Title:</span>
                    <span class="value">{{ selectedTest.title }}</span>
                </div>
                <div class="detail-row" v-if="selectedTest.title_ar">
                    <span class="label">العنوان:</span>
                    <span class="value">{{ selectedTest.title_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Type:</span>
                    <Tag>{{ getTestTypeLabel(selectedTest.test_type) }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedTest.status)">{{ selectedTest.status }}</Tag>
                </div>
                <div class="detail-row" v-if="selectedTest.overall_result">
                    <span class="label">Result:</span>
                    <Tag :severity="getResultSeverity(selectedTest.overall_result)">
                        {{ selectedTest.overall_result }}
                    </Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Objectives:</span>
                    <span class="value">{{ selectedTest.objectives }}</span>
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
import { bcmApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const tests = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedTest = ref(null)

const form = ref({
    test_id: '',
    title: '',
    title_ar: '',
    objectives: '',
    objectives_ar: '',
    scope: '',
    scenario: '',
    scenario_ar: '',
    test_type: 'tabletop',
    status: 'planned',
    scheduled_date: null
})

const testTypeOptions = [
    { label: 'Tabletop - تمرين طاولة', value: 'tabletop' },
    { label: 'Walkthrough - تمرين مرور', value: 'walkthrough' },
    { label: 'Simulation - محاكاة', value: 'simulation' },
    { label: 'Parallel - متوازي', value: 'parallel' },
    { label: 'Full Interruption - انقطاع كامل', value: 'full_interruption' }
]

const statusOptions = [
    { label: 'Planned - مخطط', value: 'planned' },
    { label: 'In Progress - قيد التنفيذ', value: 'in_progress' },
    { label: 'Completed - مكتمل', value: 'completed' },
    { label: 'Cancelled - ملغي', value: 'cancelled' }
]

const getTestTypeLabel = (type) => {
    const map = {
        tabletop: 'Tabletop',
        walkthrough: 'Walkthrough',
        simulation: 'Simulation',
        parallel: 'Parallel',
        full_interruption: 'Full Interruption'
    }
    return map[type] || type
}

const getStatusSeverity = (status) => {
    const map = {
        planned: 'info',
        in_progress: 'warn',
        completed: 'success',
        cancelled: 'secondary'
    }
    return map[status] || 'info'
}

const getResultSeverity = (result) => {
    const map = {
        passed: 'success',
        passed_with_issues: 'warn',
        failed: 'danger'
    }
    return map[result] || 'info'
}

const resetForm = () => {
    form.value = {
        test_id: '',
        title: '',
        title_ar: '',
        objectives: '',
        objectives_ar: '',
        scope: '',
        scenario: '',
        scenario_ar: '',
        test_type: 'tabletop',
        status: 'planned',
        scheduled_date: null
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = (test) => {
    isEdit.value = true
    selectedTest.value = test
    form.value = { ...test }
    dialogVisible.value = true
}

const viewTest = (test) => {
    selectedTest.value = test
    viewDialogVisible.value = true
}

const loadTests = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await bcmApi.tests.list({ organization: orgId })
        tests.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load tests:', error)
    } finally {
        loading.value = false
    }
}

const saveTest = async () => {
    if (!form.value.test_id || !form.value.title || !form.value.scenario || !form.value.scheduled_date) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill Test ID, Title, Scenario, and Scheduled Date', life: 3000 })
        return
    }
    
    saving.value = true
    try {
        // Format dates properly for Django (YYYY-MM-DD)
        const formatDate = (date) => {
            if (!date) return null;
            if (typeof date === 'string') return date.split('T')[0];
            if (date instanceof Date) return date.toISOString().split('T')[0];
            return null;
        };
        
        const data = {
            ...form.value,
            organization: appStore.currentOrganization?.id || 1,
            scheduled_date: formatDate(form.value.scheduled_date)
        }
        
        if (isEdit.value && selectedTest.value?.id) {
            await bcmApi.tests.update(selectedTest.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Test updated successfully', life: 3000 })
        } else {
            await bcmApi.tests.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Test created successfully', life: 3000 })
        }
        
        dialogVisible.value = false
        await loadTests()
    } catch (error) {
        console.error('Failed to save test:', error)
        // Extract user-friendly error message
        let errorMsg = 'Failed to save test'
        if (error.response?.data) {
            const data = error.response.data
            if (data.non_field_errors?.some(e => e.includes('unique')) || data.test_id?.some(e => e.includes('unique') || e.includes('exists'))) {
                errorMsg = 'This Test ID already exists. Please enter a different ID.'
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

const confirmDelete = (test) => {
    confirm.require({
        message: `Are you sure you want to delete "${test.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await bcmApi.tests.delete(test.id)
                await loadTests()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Test deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete test', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadTests()
})
</script>

<style scoped>
.bcm-tests-page {
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
