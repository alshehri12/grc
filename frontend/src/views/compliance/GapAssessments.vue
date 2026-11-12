<template>
    <div>
        <CrudPage ref="page" :title="$t('compliance.gap')" subtitle="تقييم الفجوات وبيان قابلية التطبيق - Gap Assessments & Statement of Applicability"
                  :api="complianceApi.gapAssessments" :columns="columns" :fields="fields" :lookups="lookups" itemLabel="gap assessment"
                  :defaults="{ status: 'draft' }" :transformIn="inn" :editable="(r) => r.status !== 'approved'" :deletable="(r) => r.status !== 'approved'" actionsWidth="210px">
            <template #header-actions>
                <Dropdown v-model="soaFramework" :options="lookups.frameworks" optionLabel="label" optionValue="value" placeholder="Statement of Applicability for..." style="min-width: 260px" />
                <Button label="SoA" icon="pi pi-list" outlined :disabled="!soaFramework" @click="openSoa" />
                <Button icon="pi pi-file-pdf" outlined severity="danger" :disabled="!soaFramework" v-tooltip="'Download SoA PDF'" @click="downloadSoa" />
            </template>
            <template #col-compliance_score="{ data }"><span class="rag" :class="scoreClass(data.compliance_score)">{{ data.compliance_score ?? '-' }}%</span></template>
            <template #col-breakdown="{ data }"><small>{{ data.implemented_controls }} impl · {{ data.partially_implemented }} partial · {{ data.not_implemented }} missing · {{ data.not_applicable }} N/A</small></template>
            <template #row-actions="{ data, reload }">
                <Button v-if="data.status !== 'approved'" icon="pi pi-refresh" text rounded v-tooltip="'Recalculate from control status'" @click="recalc(data, reload)" />
                <Button icon="pi pi-exclamation-circle" text rounded v-tooltip="'Show gaps'" @click="showGaps(data)" />
            </template>
            <template #view="{ data }">
                <div class="detail-grid" v-if="data">
                    <div><b>Assessment</b><div>{{ data.assessment_id }} - {{ data.title }}</div></div>
                    <div><b>Framework</b><div>{{ data.framework_name }}</div></div>
                    <div><b>Status / date</b><div>{{ data.status }} · {{ data.assessment_date }}</div></div>
                    <div><b>Scores</b><div>Compliance {{ data.compliance_score }}% · Maturity {{ data.maturity_score }}/5</div></div>
                    <div class="full"><b>Executive summary</b><div>{{ data.executive_summary || '-' }}</div></div>
                    <div class="full"><b>Key gaps</b><div>{{ data.key_gaps || '-' }}</div></div>
                    <div class="full"><b>Recommendations</b><div>{{ data.recommendations || '-' }}</div></div>
                </div>
            </template>
        </CrudPage>

        <Dialog v-model:visible="gapsVisible" header="Gaps (controls not fully implemented)" modal :style="{ width: '900px' }">
            <DataTable :value="gaps?.gaps || gaps || []" size="small" paginator :rows="10">
                <Column field="control_id" header="Control" /><Column field="title" header="Title" /><Column field="domain" header="Domain" />
                <Column field="status" header="Status" /><Column field="maturity_level" header="Maturity" /><Column field="owner" header="Owner" /><Column field="target_date" header="Target" />
            </DataTable>
        </Dialog>

        <Dialog v-model:visible="soaVisible" :header="`Statement of Applicability - ${soa?.framework?.code || ''}`" modal :style="{ width: '1000px' }">
            <div v-if="soa">
                <div class="stats-grid">
                    <div class="stat-card info"><span class="stat-value">{{ soa.summary.total }}</span><span class="stat-label">Controls</span></div>
                    <div class="stat-card low"><span class="stat-value">{{ soa.summary.applicable }}</span><span class="stat-label">Applicable</span></div>
                    <div class="stat-card"><span class="stat-value">{{ soa.summary.not_applicable }}</span><span class="stat-label">Excluded (N/A)</span></div>
                    <div class="stat-card critical"><span class="stat-value">{{ soa.summary.missing_justification }}</span><span class="stat-label">Exclusions without justification</span></div>
                    <div class="stat-card medium"><span class="stat-value">{{ soa.summary.no_record }}</span><span class="stat-label">No implementation record</span></div>
                </div>
                <DataTable :value="soa.rows" size="small" paginator :rows="15" :rowClass="(r) => !r.applicable && !r.justification ? 'row-warn' : ''">
                    <Column field="control_id" header="Control" style="width: 100px" /><Column field="title" header="Title" /><Column field="domain" header="Domain" />
                    <Column header="Applies"><template #body="{ data }"><i :class="data.applicable ? 'pi pi-check' : 'pi pi-times'"></i></template></Column>
                    <Column field="justification" header="Justification for exclusion" />
                    <Column field="status" header="Status" /><Column field="maturity_level" header="Mat." /><Column field="owner" header="Owner" /><Column field="evidence_accepted" header="Evid." />
                </DataTable>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useToast } from 'primevue/usetoast'
import CrudPage from '@/components/CrudPage.vue'
import { complianceApi, coreApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const toast = useToast()
const page = ref(null)
const lookups = reactive({ frameworks: [], users: [] })
const soaFramework = ref(null)
const soa = ref(null)
const soaVisible = ref(false)
const gaps = ref(null)
const gapsVisible = ref(false)
const statusOptions = ['draft', 'in_progress', 'completed', 'approved'].map(v => ({ label: v.replace('_', ' '), value: v }))
const scoreClass = (s) => s == null ? 'no_data' : s >= 80 ? 'green' : s >= 60 ? 'amber' : 'red'

const columns = [
    { field: 'assessment_id', header: 'ID', style: 'width: 150px' },
    { field: 'title', header: 'Assessment', subField: 'title_ar', style: 'min-width: 240px' },
    { field: 'framework_name', header: 'Framework' },
    { field: 'status', header: 'Status', type: 'tag', severities: { draft: 'secondary', in_progress: 'warn', completed: 'info', approved: 'success' } },
    { field: 'compliance_score', header: 'Compliance', style: 'width: 110px' },
    { field: 'maturity_score', header: 'Maturity', style: 'width: 90px' },
    { field: 'breakdown', header: 'Breakdown', sortable: false },
    { field: 'assessment_date', header: 'Date', type: 'date' },
]
const fields = [
    { name: 'framework', label: 'Framework', type: 'select', optionsKey: 'frameworks', required: true },
    { name: 'assessment_id', label: 'Assessment ID', required: true },
    { name: 'title', label: 'Title', required: true },
    { name: 'title_ar', label: 'العنوان', dir: 'rtl' },
    { name: 'status', label: 'Status', type: 'select', options: statusOptions, required: true },
    { name: 'assessment_date', label: 'Assessment date', type: 'date' },
    { name: 'assessor', label: 'Assessor', type: 'select', optionsKey: 'users' },
    { name: 'scope', label: 'Scope', type: 'textarea' },
    { name: 'executive_summary', label: 'Executive summary', type: 'textarea' },
    { name: 'key_gaps', label: 'Key gaps', type: 'textarea' },
    { name: 'recommendations', label: 'Recommendations', type: 'textarea' },
    { name: 'remediation_plan', label: 'Remediation plan', type: 'textarea' },
]
const inn = (r) => ({ ...r, assessment_date: r.assessment_date ? new Date(r.assessment_date) : null })

const recalc = async (row, reload) => {
    try { const res = await complianceApi.gapAssessments.recalculate(row.id); toast.add({ severity: 'success', summary: `Compliance ${res.data.compliance_score}%`, life: 3000 }); reload() }
    catch (e) { toast.add({ severity: 'error', summary: 'Error', detail: page.value.errorMessage(e), life: 5000 }) }
}
const showGaps = async (row) => { gaps.value = (await complianceApi.gapAssessments.gaps(row.id)).data; gapsVisible.value = true }
const openSoa = async () => {
    const orgId = await appStore.ensureOrganization()
    soa.value = (await complianceApi.soa(orgId, soaFramework.value)).data
    soaVisible.value = true
}
const downloadSoa = async () => {
    const orgId = await appStore.ensureOrganization()
    const res = await complianceApi.soaPdf(orgId, soaFramework.value)
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a'); a.href = url; a.download = 'statement-of-applicability.pdf'; a.click(); URL.revokeObjectURL(url)
}

onMounted(async () => {
    const [fws, users] = await Promise.all([complianceApi.frameworks.list({ page_size: 100 }), coreApi.users.list({ page_size: 500 })])
    lookups.frameworks = (fws.data.results || fws.data).map(f => ({ label: `${f.code} - ${f.name}`, value: f.id }))
    lookups.users = (users.data.results || users.data).map(u => ({ label: u.full_name || u.username, value: u.id }))
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
<style>
.row-warn { background: #fef3c7 !important; }
.dark-mode .row-warn { background: #78350f !important; }
</style>
