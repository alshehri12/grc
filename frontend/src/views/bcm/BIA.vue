<template>
    <div class="bia-page">
        <div class="page-header">
            <div>
                <h1>Business Impact Analysis</h1>
                <p>تحليل تأثير الأعمال</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>

        <Card>
            <template #content>
                <DataTable
                    :value="biaList"
                    :loading="loading"
                    paginator
                    :rows="10"
                    responsiveLayout="scroll"
                >
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-chart-bar" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
                        </div>
                    </template>
                    <Column field="id" header="ID" sortable style="width: 80px"></Column>
                    <Column field="function_name" header="Business Function"></Column>
                    <Column field="assessment_date" header="Assessment Date"></Column>
                    <Column field="rto_hours" header="RTO"></Column>
                    <Column field="rpo_hours" header="RPO"></Column>
                    <Column field="mtpd_hours" header="MTPD"></Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-eye" text rounded @click="viewBIA(data)" v-tooltip="$t('common.view')" />
                            <Button icon="pi pi-pencil" text rounded @click="openEditDialog(data)" v-tooltip="$t('common.edit')" />
                            <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" v-tooltip="$t('common.delete')" />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>

        <Dialog
            v-model:visible="dialogVisible"
            :header="isEdit ? 'Edit BIA - تعديل تحليل تأثير الأعمال' : 'New BIA - تحليل تأثير أعمال جديد'"
            :style="{ width: '820px' }"
            modal
        >
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>Business Function <span class="required">*</span></label>
                        <Dropdown
                            v-model="form.business_function"
                            :options="functions"
                            optionLabel="name"
                            optionValue="id"
                            placeholder="Select function"
                            filter
                        />
                    </div>
                    <div class="form-field">
                        <label>Assessment Date</label>
                        <Calendar v-model="form.assessment_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Status</label>
                        <Dropdown v-model="form.status" :options="statusOptions" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="form-field">
                        <label>Daily Financial Impact (SAR)</label>
                        <InputNumber v-model="form.financial_impact_daily" mode="decimal" :minFractionDigits="2" />
                    </div>
                </div>

                <Divider />
                <h4>Recovery Objectives - أهداف الاسترداد</h4>

                <div class="form-row">
                    <div class="form-field">
                        <label>RTO (Hours)</label>
                        <InputNumber v-model="form.rto_hours" :min="0" />
                    </div>
                    <div class="form-field">
                        <label>RPO (Hours)</label>
                        <InputNumber v-model="form.rpo_hours" :min="0" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>MTPD (Hours)</label>
                        <InputNumber v-model="form.mtpd_hours" :min="0" />
                    </div>
                    <div class="form-field">
                        <label>Minimum Staff</label>
                        <InputNumber v-model="form.minimum_staff" :min="1" />
                    </div>
                </div>

                <Divider />
                <h4>Impact Over Time (1-5) - التأثير عبر الزمن</h4>

                <div class="form-row">
                    <div class="form-field">
                        <label>1 Hour</label>
                        <Dropdown v-model="form.impact_1_hour" :options="impactOptions" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="form-field">
                        <label>4 Hours</label>
                        <Dropdown v-model="form.impact_4_hours" :options="impactOptions" optionLabel="label" optionValue="value" />
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-field">
                        <label>8 Hours</label>
                        <Dropdown v-model="form.impact_8_hours" :options="impactOptions" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="form-field">
                        <label>24 Hours</label>
                        <Dropdown v-model="form.impact_24_hours" :options="impactOptions" optionLabel="label" optionValue="value" />
                    </div>
                </div>
                <div class="form-field">
                    <label>72 Hours</label>
                    <Dropdown v-model="form.impact_72_hours" :options="impactOptions" optionLabel="label" optionValue="value" />
                </div>

                <Divider />
                <h4>Impact Narratives - أوصاف التأثير</h4>

                <div class="form-field">
                    <label>Operational Impact</label>
                    <Textarea v-model="form.operational_impact" rows="2" />
                </div>
                <div class="form-field">
                    <label>الأثر التشغيلي</label>
                    <Textarea v-model="form.operational_impact_ar" rows="2" dir="rtl" />
                </div>

                <div class="form-field">
                    <label>Reputational Impact</label>
                    <Textarea v-model="form.reputational_impact" rows="2" />
                </div>
                <div class="form-field">
                    <label>الأثر السمعة</label>
                    <Textarea v-model="form.reputational_impact_ar" rows="2" dir="rtl" />
                </div>

                <div class="form-field">
                    <label>Regulatory/Legal Impact</label>
                    <Textarea v-model="form.regulatory_impact" rows="2" />
                </div>
                <div class="form-field">
                    <label>الأثر التنظيمي/القانوني</label>
                    <Textarea v-model="form.regulatory_impact_ar" rows="2" dir="rtl" />
                </div>
            </div>

            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveBIA" :loading="saving" />
            </template>
        </Dialog>

        <Dialog
            v-model:visible="viewDialogVisible"
            header="BIA Details"
            :style="{ width: '640px' }"
            modal
        >
            <div class="view-content" v-if="selectedBIA">
                <div class="detail-row">
                    <span class="label">Business Function:</span>
                    <span class="value">{{ selectedBIA.function_name }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Assessment Date:</span>
                    <span class="value">{{ selectedBIA.assessment_date || '-' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">RTO / RPO / MTPD:</span>
                    <span class="value">{{ selectedBIA.rto_hours || '-' }} / {{ selectedBIA.rpo_hours || '-' }} / {{ selectedBIA.mtpd_hours || '-' }}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <Tag :severity="getStatusSeverity(selectedBIA.status)">{{ selectedBIA.status }}</Tag>
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
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Dialog from 'primevue/dialog'
import Divider from 'primevue/divider'
import Textarea from 'primevue/textarea'
import Calendar from 'primevue/calendar'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { bcmApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const biaList = ref([])
const functions = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const isEdit = ref(false)
const selectedBIA = ref(null)

const form = ref({
    business_function: null,
    assessment_date: null,
    status: 'draft',
    rto_hours: null,
    rpo_hours: null,
    mtpd_hours: null,
    impact_1_hour: 1,
    impact_4_hours: 2,
    impact_8_hours: 3,
    impact_24_hours: 4,
    impact_72_hours: 5,
    financial_impact_daily: null,
    operational_impact: '',
    operational_impact_ar: '',
    reputational_impact: '',
    reputational_impact_ar: '',
    regulatory_impact: '',
    regulatory_impact_ar: '',
    minimum_staff: 1
})

const impactOptions = [
    { label: '1 - Negligible (ضئيل)', value: 1 },
    { label: '2 - Minor (طفيف)', value: 2 },
    { label: '3 - Moderate (متوسط)', value: 3 },
    { label: '4 - Major (كبير)', value: 4 },
    { label: '5 - Critical (حرج)', value: 5 }
]

const statusOptions = [
    { label: 'Draft - مسودة', value: 'draft' },
    { label: 'In Progress - قيد التنفيذ', value: 'in_progress' },
    { label: 'Completed - مكتمل', value: 'completed' },
    { label: 'Approved - معتمد', value: 'approved' }
]

const getStatusSeverity = (status) => {
    const map = {
        draft: 'secondary',
        in_progress: 'warn',
        completed: 'info',
        approved: 'success'
    }
    return map[status] || 'info'
}

const formatDate = (date) => {
    if (!date) return null
    if (typeof date === 'string') return date.split('T')[0]
    if (date instanceof Date) return date.toISOString().split('T')[0]
    return null
}

const resetForm = () => {
    form.value = {
        business_function: null,
        assessment_date: null,
        status: 'draft',
        rto_hours: null,
        rpo_hours: null,
        mtpd_hours: null,
        impact_1_hour: 1,
        impact_4_hours: 2,
        impact_8_hours: 3,
        impact_24_hours: 4,
        impact_72_hours: 5,
        financial_impact_daily: null,
        operational_impact: '',
        operational_impact_ar: '',
        reputational_impact: '',
        reputational_impact_ar: '',
        regulatory_impact: '',
        regulatory_impact_ar: '',
        minimum_staff: 1
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = async (bia) => {
    isEdit.value = true
    selectedBIA.value = bia
    const response = await bcmApi.bia.get(bia.id)
    const detail = response.data
    resetForm()
    form.value = {
        ...form.value,
        ...detail,
        assessment_date: detail.assessment_date || null
    }
    dialogVisible.value = true
}

const viewBIA = (bia) => {
    selectedBIA.value = bia
    viewDialogVisible.value = true
}

const loadData = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const [biaRes, funcRes] = await Promise.all([
            bcmApi.bia.list({ organization: orgId }),
            bcmApi.functions.list({ organization: orgId })
        ])
        biaList.value = biaRes.data.results || biaRes.data
        functions.value = funcRes.data.results || funcRes.data
    } catch (error) {
        console.error('Failed to load data:', error)
    } finally {
        loading.value = false
    }
}

const saveBIA = async () => {
    if (!form.value.business_function) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please select a business function', life: 3000 })
        return
    }
    const orgId = await appStore.ensureOrganization()
    if (!orgId) {
        toast.add({ severity: 'warn', summary: 'Organization Required', detail: 'Please select an organization first', life: 3000 })
        return
    }

    saving.value = true
    try {
        const data = {
            ...form.value,
            organization: orgId,
            assessment_date: formatDate(form.value.assessment_date)
        }

        if (isEdit.value && selectedBIA.value?.id) {
            await bcmApi.bia.update(selectedBIA.value.id, data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'BIA updated successfully', life: 3000 })
        } else {
            await bcmApi.bia.create(data)
            toast.add({ severity: 'success', summary: 'Success', detail: 'BIA created successfully', life: 3000 })
        }

        dialogVisible.value = false
        await loadData()
    } catch (error) {
        console.error('Failed to save BIA:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save BIA', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (bia) => {
    confirm.require({
        message: `Are you sure you want to delete this BIA for "${bia.function_name || 'function'}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await bcmApi.bia.delete(bia.id)
                await loadData()
                toast.add({ severity: 'success', summary: 'Deleted', detail: 'BIA deleted successfully', life: 3000 })
            } catch (error) {
                toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete BIA', life: 3000 })
            }
        }
    })
}

onMounted(() => {
    loadData()
})
</script>

<style scoped>
.bia-page {
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

.form-field :deep(.p-inputnumber),
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
    min-width: 160px;
}
</style>
