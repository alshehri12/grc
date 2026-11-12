<template>
    <CrudPage ref="page" :title="$t('risk.kris')" subtitle="مؤشرات المخاطر الرئيسية - Key Risk Indicators"
              :api="riskApi.kris" :columns="columns" :fields="fields" :lookups="lookups" itemLabel="KRI" titleField="name"
              :defaults="{ direction: 'up_bad', frequency: 'monthly', is_active: true }" @loaded="loadDashboard">
        <template #above-table>
            <div class="stats-grid" v-if="dash">
                <div class="stat-card red"><span class="stat-value">{{ dash.counts.red }}</span><span class="stat-label">Red</span></div>
                <div class="stat-card amber"><span class="stat-value">{{ dash.counts.amber }}</span><span class="stat-label">Amber</span></div>
                <div class="stat-card green"><span class="stat-value">{{ dash.counts.green }}</span><span class="stat-label">Green</span></div>
                <div class="stat-card"><span class="stat-value">{{ dash.counts.no_data }}</span><span class="stat-label">No data</span></div>
                <div class="stat-card warn"><span class="stat-value">{{ dash.counts.measurement_overdue }}</span><span class="stat-label">Measurement overdue</span></div>
            </div>
        </template>
        <template #col-current_status="{ data }">
            <span class="rag" :class="data.current_status">{{ data.current_status.replace('_', ' ') }}</span>
            <i v-if="data.is_measurement_overdue" class="pi pi-clock" style="margin-left:.4rem;color:#d97706" v-tooltip="'Measurement overdue'"></i>
        </template>
        <template #col-current_value="{ data }">{{ data.current_value != null ? data.current_value + (data.unit || '') : '-' }}</template>
        <template #col-thresholds="{ data }">{{ data.warning_threshold }} / {{ data.critical_threshold }} {{ data.unit }} <small class="text-muted">({{ data.direction === 'up_bad' ? '↑ worse' : '↓ worse' }})</small></template>
        <template #row-actions="{ data }">
            <Button icon="pi pi-plus-circle" text rounded v-tooltip="'Record measurement'" @click="openMeasure(data)" />
        </template>
        <template #view="{ data }">
            <div v-if="detail">
                <div class="detail-grid">
                    <div><b>Indicator</b><div>{{ detail.kri_id }} - {{ detail.name }}</div></div>
                    <div><b>Linked risk</b><div>{{ detail.risk_code ? detail.risk_code + ' - ' + detail.risk_title : '-' }}</div></div>
                    <div><b>Thresholds</b><div>Amber {{ detail.warning_threshold }}{{ detail.unit }} · Red {{ detail.critical_threshold }}{{ detail.unit }} · Target {{ detail.target_value ?? '-' }}{{ detail.unit }}</div></div>
                    <div><b>Cadence / owner</b><div>{{ detail.frequency }} · {{ detail.owner_name || '-' }} · next due {{ detail.measurement_due_date || 'now' }}</div></div>
                    <div class="full"><b>Description</b><div>{{ detail.description || '-' }}</div></div>
                </div>
                <h4>History</h4>
                <div class="spark"><div v-for="m in [...detail.recent_measurements].reverse()" :key="m.id" class="bar" :class="m.status"
                     :style="{ height: barHeight(m.value) + '%' }" v-tooltip="`${m.measured_at}: ${m.value}${detail.unit}`"></div></div>
                <DataTable :value="detail.recent_measurements" size="small">
                    <Column field="measured_at" header="Date" /><Column field="value" header="Value" />
                    <Column header="Status"><template #body="{ data }"><span class="rag" :class="data.status">{{ data.status }}</span></template></Column>
                    <Column field="recorded_by_name" header="Recorded by" /><Column field="notes" header="Notes" />
                </DataTable>
            </div>
            <ProgressSpinner v-else style="width:40px;height:40px" />
        </template>
    </CrudPage>

    <Dialog v-model:visible="measureVisible" :header="`Record measurement - ${measure.kri?.kri_id}`" modal :style="{ width: '440px' }">
        <div class="form-field"><label>Value ({{ measure.kri?.unit }})</label><InputNumber v-model="measure.value" :maxFractionDigits="2" /></div>
        <div class="form-field"><label>Measured at</label><Calendar v-model="measure.measured_at" dateFormat="yy-mm-dd" showIcon /></div>
        <div class="form-field"><label>Notes</label><Textarea v-model="measure.notes" rows="2" autoResize /></div>
        <template #footer>
            <Button :label="$t('common.cancel')" text @click="measureVisible = false" />
            <Button :label="$t('common.save')" @click="saveMeasure" :loading="saving" />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Calendar from 'primevue/calendar'
import Textarea from 'primevue/textarea'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import CrudPage from '@/components/CrudPage.vue'
import { riskApi, coreApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const toast = useToast()
const page = ref(null)
const dash = ref(null)
const detail = ref(null)
const lookups = reactive({ risks: [], categories: [], users: [] })

const directionOptions = [{ label: 'Higher is worse (↑)', value: 'up_bad' }, { label: 'Lower is worse (↓)', value: 'down_bad' }]
const frequencyOptions = ['daily', 'weekly', 'monthly', 'quarterly'].map(v => ({ label: v, value: v }))

const columns = [
    { field: 'kri_id', header: 'ID', style: 'width: 100px' },
    { field: 'name', header: 'Indicator', subField: 'name_ar', style: 'min-width: 240px' },
    { field: 'risk_code', header: 'Risk' },
    { field: 'current_value', header: 'Current' },
    { field: 'thresholds', header: 'Amber / Red', sortable: false },
    { field: 'current_status', header: 'Status', style: 'width: 110px' },
    { field: 'last_measured_at', header: 'Measured', type: 'date' },
    { field: 'owner_name', header: 'Owner' },
]
const fields = [
    { name: 'kri_id', label: 'KRI ID', required: true, placeholder: 'KRI-009' },
    { name: 'name', label: 'Indicator name', required: true },
    { name: 'name_ar', label: 'اسم المؤشر', dir: 'rtl' },
    { name: 'risk', label: 'Linked risk', type: 'select', optionsKey: 'risks' },
    { name: 'category', label: 'Risk category', type: 'select', optionsKey: 'categories' },
    { name: 'owner', label: 'Owner', type: 'select', optionsKey: 'users' },
    { name: 'unit', label: 'Unit', placeholder: '%, count, hours' },
    { name: 'direction', label: 'Direction', type: 'select', options: directionOptions, required: true },
    { name: 'warning_threshold', label: 'Amber threshold', type: 'number', decimals: 2, required: true },
    { name: 'critical_threshold', label: 'Red threshold', type: 'number', decimals: 2, required: true },
    { name: 'target_value', label: 'Target', type: 'number', decimals: 2 },
    { name: 'frequency', label: 'Measurement frequency', type: 'select', options: frequencyOptions, required: true },
    { name: 'data_source', label: 'Data source' },
    { name: 'description', label: 'Description', type: 'textarea' },
    { name: 'is_active', label: 'Active', type: 'switch' },
]

const loadDashboard = async () => {
    const orgId = await appStore.ensureOrganization()
    dash.value = (await riskApi.kris.dashboard(orgId)).data
}

// Load the full KRI (with history) when the view dialog opens
watch(() => page.value?.$?.exposed, () => {}, { immediate: true })
const loadDetail = async (row) => { detail.value = null; detail.value = (await riskApi.kris.get(row.id)).data }
const barHeight = (v) => {
    const vals = (detail.value?.recent_measurements || []).map(m => Number(m.value))
    const max = Math.max(...vals, 1); const min = Math.min(...vals, 0)
    return max === min ? 60 : 15 + (Number(v) - min) / (max - min) * 85
}

const measureVisible = ref(false)
const saving = ref(false)
const measure = reactive({ kri: null, value: null, measured_at: new Date(), notes: '' })
const openMeasure = (row) => { Object.assign(measure, { kri: row, value: null, measured_at: new Date(), notes: '' }); measureVisible.value = true }
const saveMeasure = async () => {
    if (measure.value === null) { toast.add({ severity: 'warn', summary: 'Enter a value', life: 2500 }); return }
    saving.value = true
    try {
        const res = await riskApi.kris.measure(measure.kri.id, { value: measure.value, measured_at: measure.measured_at.toISOString().slice(0, 10), notes: measure.notes })
        toast.add({ severity: res.data.current_status === 'red' ? 'error' : 'success', summary: `Recorded - status ${res.data.current_status.toUpperCase()}`, life: 3500 })
        measureVisible.value = false
        page.value.load()
    } catch (e) { toast.add({ severity: 'error', summary: 'Error', detail: page.value.errorMessage(e), life: 5000 }) } finally { saving.value = false }
}

onMounted(async () => {
    const orgId = await appStore.ensureOrganization()
    const [risks, cats, users] = await Promise.all([riskApi.risks.list({ organization: orgId, page_size: 500 }), riskApi.categories.list(), coreApi.users.list({ page_size: 500 })])
    lookups.risks = (risks.data.results || risks.data).map(r => ({ label: `${r.risk_id} - ${r.title}`, value: r.id }))
    lookups.categories = (cats.data.results || cats.data).map(c => ({ label: c.name, value: c.id }))
    lookups.users = (users.data.results || users.data).map(u => ({ label: u.full_name || u.username, value: u.id }))
    // hook the view dialog to load details
    const origOpen = page.value.openView
    page.value.openView = (row) => { loadDetail(row); origOpen(row) }
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
<style scoped>
.spark { display: flex; align-items: flex-end; gap: 4px; height: 70px; margin: .5rem 0 1rem; padding: 4px; border-bottom: 1px solid var(--p-surface-300); }
.bar { flex: 1; min-width: 8px; border-radius: 3px 3px 0 0; opacity: .9; }
.bar.green { background: #059669; } .bar.amber { background: #d97706; } .bar.red { background: #dc2626; } .bar.no_data { background: #9ca3af; }
</style>
