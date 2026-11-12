<template>
    <CrudPage ref="page" :title="$t('risk.treatments')" subtitle="خطط معالجة المخاطر - Risk Treatment Plans"
              :api="riskApi.treatments" :columns="columns" :fields="fields" :lookups="lookups" :orgScoped="false"
              :listParams="listParams" itemLabel="treatment plan" :defaults="{ status: 'planned', progress_percentage: 0 }"
              :transformOut="out" :transformIn="inn">
        <template #above-table="{ rows }">
            <div class="stats-grid">
                <div class="stat-card" v-for="s in summary(rows)" :key="s.label" :class="s.cls">
                    <span class="stat-value">{{ s.value }}</span><span class="stat-label">{{ s.label }}</span>
                </div>
            </div>
        </template>
        <template #filters="{ reload }">
            <Dropdown v-model="listParams.risk" :options="lookups.risks" optionLabel="label" optionValue="value" placeholder="All risks" showClear filter style="min-width: 260px" />
            <Dropdown v-model="listParams.status" :options="statusOptions" optionLabel="label" optionValue="value" placeholder="All statuses" showClear />
        </template>
        <template #row-actions="{ data, reload }">
            <Button icon="pi pi-percentage" text rounded v-tooltip="'Update progress'" @click="openProgress(data)" />
        </template>
        <template #view="{ data }">
            <div class="detail-grid" v-if="data">
                <div><b>Risk</b><div>{{ data.risk_title }}</div></div>
                <div><b>Option</b><div>{{ label(optionOptions, data.treatment_option) }}</div></div>
                <div><b>Status</b><div>{{ label(statusOptions, data.status) }}</div></div>
                <div><b>Owner</b><div>{{ data.owner_name || '-' }}</div></div>
                <div><b>Start / Due</b><div>{{ data.start_date || '-' }} → {{ data.due_date || '-' }}</div></div>
                <div><b>Estimated cost</b><div>{{ data.estimated_cost ? Number(data.estimated_cost).toLocaleString() + ' SAR' : '-' }}</div></div>
                <div class="full"><b>Description</b><div>{{ data.description }}</div></div>
                <div class="full"><b>Progress</b><ProgressBar :value="Number(data.progress_percentage || 0)" /><div class="text-muted">{{ data.progress_notes }}</div></div>
            </div>
        </template>
    </CrudPage>

    <Dialog v-model:visible="progressVisible" header="Update progress" modal :style="{ width: '420px' }">
        <div class="form-field"><label>Progress %</label><InputNumber v-model="progress.progress" :min="0" :max="100" suffix="%" /></div>
        <div class="form-field"><label>Notes</label><Textarea v-model="progress.notes" rows="3" autoResize /></div>
        <template #footer>
            <Button :label="$t('common.cancel')" text @click="progressVisible = false" />
            <Button :label="$t('common.save')" @click="saveProgress" />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import ProgressBar from 'primevue/progressbar'
import { useToast } from 'primevue/usetoast'
import CrudPage from '@/components/CrudPage.vue'
import { riskApi, coreApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const toast = useToast()
const page = ref(null)
const listParams = reactive({ risk: null, status: null })
const lookups = reactive({ risks: [], users: [] })

const optionOptions = [
    { label: 'Mitigate - تخفيف', value: 'mitigate' }, { label: 'Transfer - نقل', value: 'transfer' },
    { label: 'Accept - قبول', value: 'accept' }, { label: 'Avoid - تجنب', value: 'avoid' },
]
const statusOptions = [
    { label: 'Planned', value: 'planned' }, { label: 'In Progress', value: 'in_progress' }, { label: 'Completed', value: 'completed' },
    { label: 'Deferred', value: 'deferred' }, { label: 'Cancelled', value: 'cancelled' },
]
const label = (opts, v) => (opts.find(o => o.value === v) || {}).label || v

const columns = [
    { field: 'risk_title', header: 'Risk', style: 'min-width: 220px' },
    { field: 'title', header: 'Treatment', subField: 'title_ar' },
    { field: 'treatment_option', header: 'Option', type: 'tag', options: optionOptions, severities: { mitigate: 'info', transfer: 'warn', accept: 'secondary', avoid: 'danger' } },
    { field: 'status', header: 'Status', type: 'tag', options: statusOptions, severities: { planned: 'info', in_progress: 'warn', completed: 'success', deferred: 'secondary', cancelled: 'danger' } },
    { field: 'progress_percentage', header: 'Progress', type: 'progress', style: 'width: 140px' },
    { field: 'due_date', header: 'Due', type: 'date' },
    { field: 'owner_name', header: 'Owner' },
]
const fields = [
    { name: 'risk', label: 'Risk', type: 'select', optionsKey: 'risks', required: true },
    { name: 'treatment_option', label: 'Treatment option', type: 'select', options: optionOptions, required: true },
    { name: 'title', label: 'Title', required: true },
    { name: 'title_ar', label: 'Title (Arabic)', dir: 'rtl' },
    { name: 'description', label: 'Description', type: 'textarea', required: true },
    { name: 'owner', label: 'Owner', type: 'select', optionsKey: 'users' },
    { name: 'status', label: 'Status', type: 'select', options: statusOptions, required: true },
    { name: 'estimated_cost', label: 'Estimated cost (SAR)', type: 'number' },
    { name: 'start_date', label: 'Start date', type: 'date' },
    { name: 'due_date', label: 'Due date', type: 'date' },
    { name: 'expected_residual_likelihood', label: 'Expected residual likelihood (1-5)', type: 'number', min: 1, max: 5 },
    { name: 'expected_residual_impact', label: 'Expected residual impact (1-5)', type: 'number', min: 1, max: 5 },
    { name: 'progress_percentage', label: 'Progress %', type: 'number', min: 0, max: 100 },
    { name: 'progress_notes', label: 'Progress notes', type: 'textarea' },
]
const out = (p) => { delete p.organization; return p }
const inn = (r) => ({ ...r, start_date: r.start_date ? new Date(r.start_date) : null, due_date: r.due_date ? new Date(r.due_date) : null })

const summary = (rows) => [
    { label: 'Planned', value: rows.filter(r => r.status === 'planned').length, cls: 'medium' },
    { label: 'In progress', value: rows.filter(r => r.status === 'in_progress').length, cls: 'high' },
    { label: 'Completed', value: rows.filter(r => r.status === 'completed').length, cls: 'low' },
    { label: 'Overdue', value: rows.filter(r => ['planned', 'in_progress'].includes(r.status) && r.due_date && r.due_date < new Date().toISOString().slice(0, 10)).length, cls: 'critical' },
]

const progressVisible = ref(false)
const progress = reactive({ id: null, progress: 0, notes: '' })
const openProgress = (row) => { progress.id = row.id; progress.progress = Number(row.progress_percentage || 0); progress.notes = row.progress_notes || ''; progressVisible.value = true }
const saveProgress = async () => {
    try {
        await riskApi.treatments.updateProgress(progress.id, progress.progress, progress.notes)
        progressVisible.value = false
        page.value.load()
    } catch (e) { toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to update progress', life: 3000 }) }
}

onMounted(async () => {
    const orgId = await appStore.ensureOrganization()
    const [risks, users] = await Promise.all([riskApi.risks.list({ organization: orgId, page_size: 500 }), coreApi.users.list({ page_size: 500 })])
    lookups.risks = (risks.data.results || risks.data).map(r => ({ label: `${r.risk_id} - ${r.title}`, value: r.id }))
    lookups.users = (users.data.results || users.data).map(u => ({ label: u.full_name || u.username, value: u.id }))
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
