<template>
    <div>
        <TabView v-model:activeIndex="tab">
            <TabPanel header="Audit findings">
                <CrudPage ref="findingsPage" :title="$t('compliance.findings')" subtitle="ملاحظات التدقيق - Audit Findings"
                          :api="complianceApi.findings" :columns="findingColumns" :fields="findingFields" :lookups="lookups" :orgScoped="false"
                          itemLabel="finding" :defaults="{ finding_type: 'observation', status: 'open' }" :transformIn="inn" :transformOut="noOrg" @loaded="findings = $event">
                    <template #above-table="{ rows }">
                        <div class="stats-grid">
                            <div class="stat-card critical"><span class="stat-value">{{ rows.filter(r => r.finding_type === 'major_nc' && r.status !== 'closed').length }}</span><span class="stat-label">Open major NCs</span></div>
                            <div class="stat-card high"><span class="stat-value">{{ rows.filter(r => r.finding_type === 'minor_nc' && r.status !== 'closed').length }}</span><span class="stat-label">Open minor NCs</span></div>
                            <div class="stat-card medium"><span class="stat-value">{{ rows.filter(r => r.status === 'overdue').length }}</span><span class="stat-label">Overdue</span></div>
                            <div class="stat-card low"><span class="stat-value">{{ rows.filter(r => r.status === 'closed').length }}</span><span class="stat-label">Closed</span></div>
                        </div>
                    </template>
                    <template #row-actions="{ data }">
                        <Button icon="pi pi-wrench" text rounded v-tooltip="'Raise corrective action'" @click="raiseCar(data)" />
                    </template>
                    <template #view="{ data }">
                        <div class="detail-grid" v-if="data">
                            <div><b>Finding</b><div>{{ data.finding_id }} - {{ data.title }}</div></div>
                            <div><b>Audit</b><div>{{ data.audit_title }}</div></div>
                            <div><b>Type / status</b><div>{{ data.finding_type }} · {{ data.status }}</div></div>
                            <div><b>Criteria</b><div>{{ data.criteria_reference || '-' }}</div></div>
                            <div><b>Assigned / due</b><div>{{ data.assigned_to_name || '-' }} · {{ data.due_date || '-' }}</div></div>
                            <div><b>Risk rating</b><div>{{ data.risk_rating || '-' }}</div></div>
                            <div class="full"><b>Description</b><div>{{ data.description }}</div></div>
                            <div class="full"><b>Recommendation</b><div>{{ data.recommendation }}</div></div>
                            <div class="full" v-if="data.management_response"><b>Management response</b><div>{{ data.management_response }}</div></div>
                            <div class="full"><b>Corrective actions</b>
                                <ul class="issue-list"><li v-for="c in cars.filter(c => c.finding === data.id)" :key="c.id">{{ c.car_id }} - {{ c.title }} <Tag :severity="carSev[c.status]">{{ c.status }}</Tag></li></ul>
                            </div>
                        </div>
                    </template>
                </CrudPage>
            </TabPanel>
            <TabPanel header="Corrective actions">
                <CrudPage ref="carPage" title="Corrective Actions" subtitle="الإجراءات التصحيحية - Corrective Action Requests (CAR)"
                          :api="complianceApi.correctiveActions" :columns="carColumns" :fields="carFields" :lookups="lookups" itemLabel="corrective action"
                          :defaults="carDefaults" :transformIn="inn" @loaded="cars = $event">
                    <template #above-table="{ rows }">
                        <div class="stats-grid">
                            <div class="stat-card high"><span class="stat-value">{{ rows.filter(r => ['open','in_progress'].includes(r.status)).length }}</span><span class="stat-label">Open / in progress</span></div>
                            <div class="stat-card critical"><span class="stat-value">{{ rows.filter(r => r.status === 'overdue').length }}</span><span class="stat-label">Overdue</span></div>
                            <div class="stat-card medium"><span class="stat-value">{{ rows.filter(r => r.status === 'pending_verification').length }}</span><span class="stat-label">Awaiting verification</span></div>
                            <div class="stat-card low"><span class="stat-value">{{ rows.filter(r => ['verified','closed'].includes(r.status)).length }}</span><span class="stat-label">Verified / closed</span></div>
                        </div>
                    </template>
                    <template #row-actions="{ data, reload }">
                        <Button v-if="!['verified','closed'].includes(data.status) && authStore.canApprove" icon="pi pi-verified" text rounded severity="success" v-tooltip="'Verify (independent)'" @click="verify(data, reload)" />
                    </template>
                    <template #view="{ data }">
                        <div class="detail-grid" v-if="data">
                            <div><b>CAR</b><div>{{ data.car_id }} - {{ data.title }}</div></div>
                            <div><b>Finding</b><div>{{ data.finding_title }}</div></div>
                            <div><b>Status / priority</b><div>{{ data.status }} · {{ data.priority }}</div></div>
                            <div><b>Owner / target</b><div>{{ data.owner_name || '-' }} · {{ data.target_date }}</div></div>
                            <div class="full"><b>Root cause</b><div>{{ data.root_cause || '-' }}</div></div>
                            <div class="full"><b>Action</b><div>{{ data.action_description || '-' }}</div></div>
                            <div class="full"><b>Verification</b><div>{{ data.verification_method || '-' }} <span v-if="data.verified_by_name">· verified by {{ data.verified_by_name }} on {{ data.verified_date }}</span></div></div>
                        </div>
                    </template>
                </CrudPage>
            </TabPanel>
        </TabView>

        <Dialog v-model:visible="verifyVisible" header="Verify corrective action" modal :style="{ width: '460px' }">
            <p class="text-muted">Verification must be independent: the owner who implemented the action cannot verify it.</p>
            <div class="form-field"><label>Verification notes</label><Textarea v-model="verifyForm.notes" rows="3" autoResize /></div>
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="verifyVisible = false" />
                <Button label="Verify" severity="success" @click="submitVerify" :loading="busy" />
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import CrudPage from '@/components/CrudPage.vue'
import { complianceApi, coreApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const appStore = useAppStore()
const authStore = useAuthStore()
const toast = useToast()
const tab = ref(0)
const findingsPage = ref(null)
const carPage = ref(null)
const findings = ref([])
const cars = ref([])
const lookups = reactive({ audits: [], controls: [], users: [], departments: [], findings: [] })
const carDefaults = reactive({ status: 'open', priority: 'medium' })

const typeOptions = [{ label: 'Major non-conformity', value: 'major_nc' }, { label: 'Minor non-conformity', value: 'minor_nc' }, { label: 'Observation', value: 'observation' }, { label: 'Opportunity', value: 'opportunity' }, { label: 'Positive', value: 'positive' }]
const fStatus = ['open', 'in_progress', 'pending_verification', 'closed', 'overdue'].map(v => ({ label: v.replace('_', ' '), value: v }))
const cStatus = ['open', 'in_progress', 'pending_verification', 'verified', 'closed', 'overdue'].map(v => ({ label: v.replace('_', ' '), value: v }))
const prio = ['low', 'medium', 'high', 'critical'].map(v => ({ label: v, value: v }))
const typeSev = { major_nc: 'danger', minor_nc: 'warn', observation: 'info', opportunity: 'secondary', positive: 'success' }
const statSev = { open: 'info', in_progress: 'warn', pending_verification: 'warn', closed: 'success', overdue: 'danger' }
const carSev = { ...statSev, verified: 'success' }

const findingColumns = [
    { field: 'finding_id', header: 'ID', style: 'width: 150px' },
    { field: 'title', header: 'Finding', style: 'min-width: 260px' },
    { field: 'audit_title', header: 'Audit' },
    { field: 'finding_type', header: 'Type', type: 'tag', options: typeOptions, severities: typeSev },
    { field: 'status', header: 'Status', type: 'tag', severities: statSev },
    { field: 'due_date', header: 'Due', type: 'date' },
    { field: 'assigned_to_name', header: 'Assigned' },
]
const findingFields = [
    { name: 'audit', label: 'Audit', type: 'select', optionsKey: 'audits', required: true },
    { name: 'finding_id', label: 'Finding ID', required: true },
    { name: 'title', label: 'Title', required: true, full: true },
    { name: 'finding_type', label: 'Type', type: 'select', options: typeOptions, required: true },
    { name: 'status', label: 'Status', type: 'select', options: fStatus, required: true },
    { name: 'control', label: 'Control', type: 'select', optionsKey: 'controls' },
    { name: 'criteria_reference', label: 'Criteria reference' },
    { name: 'assigned_to', label: 'Assigned to', type: 'select', optionsKey: 'users' },
    { name: 'department', label: 'Department', type: 'select', optionsKey: 'departments' },
    { name: 'due_date', label: 'Due date', type: 'date' },
    { name: 'risk_rating', label: 'Risk rating' },
    { name: 'description', label: 'Description', type: 'textarea', required: true },
    { name: 'recommendation', label: 'Recommendation', type: 'textarea' },
    { name: 'management_response', label: 'Management response', type: 'textarea' },
]
const carColumns = [
    { field: 'car_id', header: 'ID', style: 'width: 130px' },
    { field: 'title', header: 'Action', style: 'min-width: 260px' },
    { field: 'finding_title', header: 'Finding' },
    { field: 'priority', header: 'Priority', type: 'tag', severities: { low: 'secondary', medium: 'info', high: 'warn', critical: 'danger' } },
    { field: 'status', header: 'Status', type: 'tag', severities: carSev },
    { field: 'target_date', header: 'Target', type: 'date' },
    { field: 'owner_name', header: 'Owner' },
]
const carFields = [
    { name: 'finding', label: 'Finding', type: 'select', optionsKey: 'findings', required: true, full: true },
    { name: 'car_id', label: 'CAR ID', required: true },
    { name: 'title', label: 'Title', required: true },
    { name: 'priority', label: 'Priority', type: 'select', options: prio, required: true },
    { name: 'status', label: 'Status', type: 'select', options: cStatus, required: true },
    { name: 'owner', label: 'Owner', type: 'select', optionsKey: 'users' },
    { name: 'target_date', label: 'Target date', type: 'date', required: true },
    { name: 'root_cause', label: 'Root cause', type: 'textarea' },
    { name: 'action_description', label: 'Action description', type: 'textarea' },
    { name: 'verification_method', label: 'Verification method', type: 'textarea' },
]
const inn = (r) => { const d = { ...r }; ['due_date', 'target_date'].forEach(k => { if (d[k]) d[k] = new Date(d[k]) }); return d }
const noOrg = (p) => { delete p.organization; return p }

// Pre-fill a corrective action from a finding (no id -> CrudPage saves it as a new record).
const raiseCar = (finding) => {
    tab.value = 1
    setTimeout(() => carPage.value?.openEdit({
        finding: finding.id, title: `Remediate: ${finding.title}`, status: 'open',
        priority: finding.finding_type === 'major_nc' ? 'high' : 'medium', target_date: finding.due_date,
    }), 50)
}

const verifyVisible = ref(false)
const busy = ref(false)
const verifyForm = reactive({ row: null, notes: '', reload: null })
const verify = (row, reload) => { Object.assign(verifyForm, { row, notes: '', reload }); verifyVisible.value = true }
const submitVerify = async () => {
    busy.value = true
    try { await complianceApi.correctiveActions.verify(verifyForm.row.id, verifyForm.notes); verifyVisible.value = false; verifyForm.reload(); toast.add({ severity: 'success', summary: 'Verified', life: 2500 }) }
    catch (e) { toast.add({ severity: 'error', summary: 'Not allowed', detail: carPage.value.errorMessage(e), life: 5000 }) }
    finally { busy.value = false }
}

onMounted(async () => {
    const orgId = await appStore.ensureOrganization()
    const p = { organization: orgId, page_size: 500 }
    const [audits, controls, users, depts, fnd] = await Promise.all([
        complianceApi.audits.list(p), complianceApi.controls.list({ page_size: 500 }), coreApi.users.list({ page_size: 500 }),
        coreApi.departments.list(p), complianceApi.findings.list({ page_size: 500 })])
    const rows = (r) => r.data.results || r.data
    lookups.audits = rows(audits).map(a => ({ label: `${a.audit_id} - ${a.title}`, value: a.id }))
    lookups.controls = rows(controls).map(c => ({ label: `${c.control_id} - ${c.title}`, value: c.id }))
    lookups.users = rows(users).map(u => ({ label: u.full_name || u.username, value: u.id }))
    lookups.departments = rows(depts).map(d => ({ label: d.name, value: d.id }))
    lookups.findings = rows(fnd).map(f => ({ label: `${f.finding_id} - ${f.title}`, value: f.id }))
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
