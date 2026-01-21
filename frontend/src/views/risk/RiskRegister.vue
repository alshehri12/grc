<template>
    <div class="risk-register-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('risk.register') }}</h1>
                <p>سجل المخاطر - Risk Register</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>
        
        <!-- Statistics Cards -->
        <div class="stats-grid">
            <div class="stat-card critical">
                <span class="stat-value">{{ stats.critical || 0 }}</span>
                <span class="stat-label">Critical - حرج</span>
            </div>
            <div class="stat-card high">
                <span class="stat-value">{{ stats.high || 0 }}</span>
                <span class="stat-label">High - عالي</span>
            </div>
            <div class="stat-card medium">
                <span class="stat-value">{{ stats.medium || 0 }}</span>
                <span class="stat-label">Medium - متوسط</span>
            </div>
            <div class="stat-card low">
                <span class="stat-value">{{ stats.low || 0 }}</span>
                <span class="stat-label">Low - منخفض</span>
            </div>
        </div>
        
        <!-- Risks Table -->
        <Card>
            <template #content>
                <DataTable 
                    :value="risks" 
                    :loading="loading"
                    paginator 
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-exclamation-triangle" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="risk_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Risk Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="risk_type" header="Type">
                        <template #body="{ data }">
                            <Tag>{{ data.risk_type }}</Tag>
                        </template>
                    </Column>
                    <Column header="Risk Score">
                        <template #body="{ data }">
                            <div class="risk-score" :class="getRiskLevel(data.inherent_risk_score)">
                                {{ data.inherent_risk_score || (data.inherent_likelihood * data.inherent_impact) }}
                            </div>
                        </template>
                    </Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewRisk(data)" v-tooltip="$t('common.view')" />
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
            :header="isEdit ? $t('risk.editRisk') : $t('risk.newRisk')"
            :style="{ width: '750px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.id') }} <span class="required">*</span></label>
                        <InputText v-model="form.risk_id" placeholder="RSK-001" />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('risk.riskType') }}</label>
                        <Dropdown 
                            v-model="form.risk_type" 
                            :options="riskTypeOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            :placeholder="$t('common.selectType')"
                        />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.title') }} <span class="required">*</span></label>
                        <InputText v-model="form.title" :placeholder="$t('risk.riskTitlePlaceholder')" />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('common.titleAr') }}</label>
                        <InputText v-model="form.title_ar" placeholder="عنوان المخاطر" dir="rtl" />
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('common.description') }}</label>
                        <Textarea v-model="form.description" rows="2" placeholder="Risk description..." />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('common.descriptionAr') }}</label>
                        <Textarea v-model="form.description_ar" rows="2" placeholder="وصف المخاطر..." dir="rtl" />
                    </div>
                </div>
                
                <Divider />
                
                <h4>{{ $t('risk.inherentRisk') }}</h4>
                
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ $t('risk.likelihood') }} (1-5) <span class="required">*</span></label>
                        <Dropdown 
                            v-model="form.inherent_likelihood" 
                            :options="likelihoodOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select likelihood"
                        />
                    </div>
                    <div class="form-field">
                        <label>{{ $t('risk.impact') }} (1-5) <span class="required">*</span></label>
                        <Dropdown 
                            v-model="form.inherent_impact" 
                            :options="impactOptions" 
                            optionLabel="label" 
                            optionValue="value"
                            placeholder="Select impact"
                        />
                    </div>
                </div>
                
                <div class="risk-preview" v-if="form.inherent_likelihood && form.inherent_impact">
                    <span class="preview-label">Risk Score:</span>
                    <span class="preview-score" :class="getRiskLevel(form.inherent_likelihood * form.inherent_impact)">
                        {{ form.inherent_likelihood * form.inherent_impact }}
                    </span>
                    <span class="preview-level">{{ getRiskLevelLabel(form.inherent_likelihood * form.inherent_impact) }}</span>
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
                    <div class="form-field">
                        <label>Review Date</label>
                        <Calendar v-model="form.review_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                </div>
            </div>
            
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveRisk" :loading="saving" />
            </template>
        </Dialog>
        
        <!-- View Dialog -->
        <Dialog 
            v-model:visible="viewDialogVisible" 
            :header="selectedRisk?.title || 'Risk Details'"
            :style="{ width: '600px' }"
            modal
        >
            <div class="view-content" v-if="selectedRisk">
                <div class="detail-row">
                    <span class="label">Risk ID:</span>
                    <span class="value">{{ selectedRisk.risk_id }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Title:</span>
                    <span class="value">{{ selectedRisk.title }}</span>
                </div>
                <div class="detail-row" v-if="selectedRisk.title_ar">
                    <span class="label">العنوان:</span>
                    <span class="value">{{ selectedRisk.title_ar }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Type:</span>
                    <Tag>{{ selectedRisk.risk_type }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedRisk.status)">{{ selectedRisk.status }}</Tag>
                </div>
                <div class="detail-row">
                    <span class="label">Risk Score:</span>
                    <span class="risk-score" :class="getRiskLevel(selectedRisk.inherent_likelihood * selectedRisk.inherent_impact)">
                        {{ selectedRisk.inherent_likelihood * selectedRisk.inherent_impact }}
                    </span>
                </div>
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{{ selectedRisk.description }}</span>
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
import { riskApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const risks = ref([])
const stats = ref({})
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedRisk = ref(null)

const form = ref({
    risk_id: '',
    title: '',
    title_ar: '',
    description: '',
    description_ar: '',
    risk_source: '',
    risk_type: 'operational',
    status: 'identified',
    inherent_likelihood: 3,
    inherent_impact: 3,
    review_date: null
})

const riskTypeOptions = [
    { label: 'Strategic - استراتيجي', value: 'strategic' },
    { label: 'Operational - تشغيلي', value: 'operational' },
    { label: 'Financial - مالي', value: 'financial' },
    { label: 'Compliance - امتثال', value: 'compliance' },
    { label: 'Cybersecurity - سيبراني', value: 'cyber' },
    { label: 'Reputational - سمعي', value: 'reputational' }
]

const statusOptions = [
    { label: 'Identified - محدد', value: 'identified' },
    { label: 'Assessed - مقيم', value: 'assessed' },
    { label: 'Treating - قيد المعالجة', value: 'treating' },
    { label: 'Monitoring - مراقب', value: 'monitoring' },
    { label: 'Closed - مغلق', value: 'closed' }
]

const likelihoodOptions = [
    { label: '1 - Rare (نادر)', value: 1 },
    { label: '2 - Unlikely (غير مرجح)', value: 2 },
    { label: '3 - Possible (ممكن)', value: 3 },
    { label: '4 - Likely (مرجح)', value: 4 },
    { label: '5 - Almost Certain (شبه مؤكد)', value: 5 }
]

const impactOptions = [
    { label: '1 - Negligible (ضئيل)', value: 1 },
    { label: '2 - Minor (طفيف)', value: 2 },
    { label: '3 - Moderate (متوسط)', value: 3 },
    { label: '4 - Major (كبير)', value: 4 },
    { label: '5 - Catastrophic (كارثي)', value: 5 }
]

const getRiskLevel = (score) => {
    if (score >= 20) return 'critical'
    if (score >= 12) return 'high'
    if (score >= 6) return 'medium'
    return 'low'
}

const getRiskLevelLabel = (score) => {
    if (score >= 20) return 'Critical - حرج'
    if (score >= 12) return 'High - عالي'
    if (score >= 6) return 'Medium - متوسط'
    return 'Low - منخفض'
}

const getStatusSeverity = (status) => {
    const map = {
        identified: 'info',
        assessed: 'info',
        treating: 'warn',
        monitoring: 'success',
        closed: 'secondary'
    }
    return map[status] || 'info'
}

const resetForm = () => {
    form.value = {
        risk_id: '',
        title: '',
        title_ar: '',
        description: '',
        description_ar: '',
        risk_source: '',
        risk_type: 'operational',
        status: 'identified',
        inherent_likelihood: 3,
        inherent_impact: 3,
        review_date: null
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = (risk) => {
    isEdit.value = true
    selectedRisk.value = risk
    form.value = { ...risk }
    dialogVisible.value = true
}

const viewRisk = (risk) => {
    selectedRisk.value = risk
    viewDialogVisible.value = true
}

const loadRisks = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const [risksRes, statsRes] = await Promise.all([
            riskApi.risks.list({ organization: orgId }),
            riskApi.risks.statistics(orgId)
        ])
        risks.value = risksRes.data.results || risksRes.data
        stats.value = statsRes.data?.by_level || {}
    } catch (error) {
        console.error('Failed to load risks:', error)
    } finally {
        loading.value = false
    }
}

const saveRisk = async () => {
    if (!form.value.risk_id || !form.value.title) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill Risk ID and Title', life: 3000 })
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
            review_date: formatDate(form.value.review_date)
        }
        
        if (isEdit.value && selectedRisk.value?.id) {
            await riskApi.risks.update(selectedRisk.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Risk updated successfully', life: 3000 })
        } else {
            await riskApi.risks.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'Risk created successfully', life: 3000 })
        }
        
        dialogVisible.value = false
        await loadRisks()
    } catch (error) {
        console.error('Failed to save risk:', error)
        // Extract user-friendly error message
        let errorMsg = 'Failed to save risk'
        if (error.response?.data) {
            const data = error.response.data
            if (data.non_field_errors?.some(e => e.includes('unique')) || data.risk_id?.some(e => e.includes('unique') || e.includes('exists'))) {
                errorMsg = 'This Risk ID already exists. Please enter a different ID.'
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

const confirmDelete = (risk) => {
    confirm.require({
        message: `Are you sure you want to delete "${risk.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await riskApi.risks.delete(risk.id)
                await loadRisks()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'Risk deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete risk', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadRisks()
})
</script>

<style scoped>
.risk-register-page {
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

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
}

@media (max-width: 768px) {
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

.stat-card {
    background: var(--p-surface-0);
    border-radius: 8px;
    padding: 1.25rem;
    text-align: center;
    border-left: 4px solid;
}

.stat-card.critical { border-color: #dc2626; }
.stat-card.high { border-color: #ea580c; }
.stat-card.medium { border-color: #ca8a04; }
.stat-card.low { border-color: #16a34a; }

.stat-value { font-size: 2rem; font-weight: 700; display: block; }
.stat-label { font-size: 0.85rem; color: var(--p-text-muted-color); }

.risk-score {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-weight: 600;
}

.risk-score.critical { background: rgba(220, 38, 38, 0.1); color: #dc2626; }
.risk-score.high { background: rgba(234, 88, 12, 0.1); color: #ea580c; }
.risk-score.medium { background: rgba(202, 138, 4, 0.1); color: #ca8a04; }
.risk-score.low { background: rgba(22, 163, 74, 0.1); color: #16a34a; }

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

.risk-preview {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: var(--p-surface-100);
    border-radius: 8px;
}

.preview-label {
    font-weight: 600;
}

.preview-score {
    font-size: 1.5rem;
    font-weight: 700;
    padding: 0.5rem 1rem;
    border-radius: 8px;
}

.preview-level {
    color: var(--p-text-muted-color);
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
