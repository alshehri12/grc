<template>
    <CrudPage ref="page" :title="$t('bcm.incidents')" subtitle="الحوادث وإدارة الأزمات - Incidents & Crisis Management"
              :api="bcmApi.incidents" :columns="columns" :fields="fields" :lookups="lookups" itemLabel="incident"
              :defaults="{ severity: 'medium', status: 'reported', incident_type: 'operational', related_risks: [], affected_functions: [] }"
              :transformIn="inn" :transformOut="out" dialogWidth="860px" actionsWidth="200px">
        <template #above-table="{ rows }">
            <div class="stats-grid">
                <div class="stat-card critical"><span class="stat-value">{{ rows.filter(r => !['resolved','closed'].includes(r.status)).length }}</span><span class="stat-label">Active incidents</span></div>
                <div class="stat-card high"><span class="stat-value">{{ rows.filter(r => r.severity === 'critical' && !['resolved','closed'].includes(r.status)).length }}</span><span class="stat-label">Critical & active</span></div>
                <div class="stat-card low"><span class="stat-value">{{ rows.filter(r => ['resolved','closed'].includes(r.status)).length }}</span><span class="stat-label">Resolved / closed</span></div>
                <div class="stat-card info"><span class="stat-value">{{ rows.filter(r => r.activated_bc_plan || r.activated_dr_plan).length }}</span><span class="stat-label">Plans activated</span></div>
            </div>
        </template>
        <template #row-actions="{ data, reload }">
            <Button v-if="['reported','assessing'].includes(data.status)" icon="pi pi-bolt" text rounded severity="danger" v-tooltip="'Declare crisis / start response'" @click="act(data, 'declareCrisis', reload)" />
            <Button v-if="['responding','recovering','assessing'].includes(data.status)" icon="pi pi-check-circle" text rounded severity="success" v-tooltip="'Resolve'" @click="openResolve(data, reload)" />
        </template>
        <template #view="{ data }">
            <div class="detail-grid" v-if="data">
                <div><b>Incident</b><div>{{ data.incident_id }} - {{ data.title }}</div></div>
                <div><b>Type / severity</b><div>{{ data.incident_type }} · <Tag :severity="sevSeverity[data.severity]">{{ data.severity }}</Tag></div></div>
                <div><b>Status</b><div><Tag :severity="statusSeverity[data.status]">{{ data.status }}</Tag></div></div>
                <div><b>Commander</b><div>{{ data.incident_commander_name || '-' }}</div></div>
                <div><b>Reported / declared</b><div>{{ fmt(data.reported_at) }} / {{ fmt(data.declared_at) }}</div></div>
                <div><b>Resolved</b><div>{{ fmt(data.resolved_at) }}</div></div>
                <div><b>Activated plans</b><div>{{ planName(lookups.bcPlans, data.activated_bc_plan) }} {{ planName(lookups.drPlans, data.activated_dr_plan) }}</div></div>
                <div><b>Estimated loss</b><div>{{ data.financial_loss ? Number(data.financial_loss).toLocaleString() + ' SAR' : '-' }}</div></div>
                <div class="full"><b>Materialised risks</b><div><Tag v-for="r in data.related_risks" :key="r" severity="warn" style="margin:.1rem">{{ riskLabel(r) }}</Tag><span v-if="!data.related_risks?.length">-</span></div></div>
                <div class="full"><b>Description</b><div>{{ data.description }}</div></div>
                <div class="full"><b>Impact</b><div>{{ data.impact_description }}</div></div>
                <div class="full" v-if="data.response_actions"><b>Response actions</b><div>{{ data.response_actions }}</div></div>
                <div class="full" v-if="data.lessons_learned"><b>Lessons learned</b><div>{{ data.lessons_learned }}</div></div>
            </div>
        </template>
    </CrudPage>

    <Dialog v-model:visible="resolveVisible" header="Resolve incident" modal :style="{ width: '520px' }">
        <p class="text-muted">Resolving records the time, notifies linked risk owners (re-assessment tasks were created when risks were linked) and feeds the lessons learned into the BCM programme.</p>
        <div class="form-field"><label>Lessons learned</label><Textarea v-model="resolveForm.lessons" rows="4" autoResize /></div>
        <template #footer>
            <Button :label="$t('common.cancel')" text @click="resolveVisible = false" />
            <Button label="Resolve" severity="success" @click="submitResolve" :loading="busy" />
        </template>
    </Dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import CrudPage from '@/components/CrudPage.vue'
import { bcmApi, riskApi, coreApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const toast = useToast()
const page = ref(null)
const lookups = reactive({ risks: [], functions: [], users: [], bcPlans: [], drPlans: [], teams: [] })

const typeOptions = ['natural_disaster', 'cyber_attack', 'infrastructure', 'pandemic', 'security', 'operational', 'other'].map(v => ({ label: v.replace('_', ' '), value: v }))
const severityOptions = ['low', 'medium', 'high', 'critical'].map(v => ({ label: v, value: v }))
const statusOptions = ['reported', 'assessing', 'responding', 'recovering', 'resolved', 'closed'].map(v => ({ label: v, value: v }))
const sevSeverity = { low: 'success', medium: 'info', high: 'warn', critical: 'danger' }
const statusSeverity = { reported: 'info', assessing: 'warn', responding: 'danger', recovering: 'warn', resolved: 'success', closed: 'secondary' }
const fmt = (v) => v ? new Date(v).toLocaleString() : '-'
const riskLabel = (id) => (lookups.risks.find(r => r.value === id) || {}).label || id
const planName = (opts, id) => id ? ((opts.find(p => p.value === id) || {}).label || '') : ''

const columns = [
    { field: 'incident_id', header: 'ID', style: 'width: 130px' },
    { field: 'title', header: 'Incident', subField: 'title_ar', style: 'min-width: 240px' },
    { field: 'incident_type', header: 'Type', type: 'tag', options: typeOptions },
    { field: 'severity', header: 'Severity', type: 'tag', severities: sevSeverity },
    { field: 'status', header: 'Status', type: 'tag', severities: statusSeverity },
    { field: 'reported_at', header: 'Reported', type: 'date' },
]
const fields = [
    { name: 'incident_id', label: 'Incident ID', required: true, placeholder: 'INC-2026-007' },
    { name: 'incident_type', label: 'Type', type: 'select', options: typeOptions, required: true },
    { name: 'title', label: 'Title', required: true },
    { name: 'title_ar', label: 'العنوان', dir: 'rtl' },
    { name: 'severity', label: 'Severity', type: 'select', options: severityOptions, required: true },
    { name: 'status', label: 'Status', type: 'select', options: statusOptions, required: true },
    { name: 'reported_at', label: 'Reported at', type: 'date', required: true },
    { name: 'incident_commander', label: 'Incident commander', type: 'select', optionsKey: 'users' },
    { name: 'crisis_team', label: 'Crisis team', type: 'select', optionsKey: 'teams' },
    { name: 'financial_loss', label: 'Estimated financial loss (SAR)', type: 'number' },
    { name: 'activated_bc_plan', label: 'Activated BC plan', type: 'select', optionsKey: 'bcPlans' },
    { name: 'activated_dr_plan', label: 'Activated DR plan', type: 'select', optionsKey: 'drPlans' },
    { name: 'affected_functions', label: 'Affected business functions', type: 'multiselect', optionsKey: 'functions' },
    { name: 'related_risks', label: 'Materialised risks (creates re-assessment tasks for their owners)', type: 'multiselect', optionsKey: 'risks' },
    { name: 'description', label: 'Description', type: 'textarea', required: true },
    { name: 'impact_description', label: 'Impact description', type: 'textarea', required: true },
    { name: 'response_actions', label: 'Response actions', type: 'textarea' },
    { name: 'lessons_learned', label: 'Lessons learned', type: 'textarea' },
]
const inn = (r) => ({ ...r, reported_at: r.reported_at ? new Date(r.reported_at) : null })
const out = (p) => { if (p.reported_at && p.reported_at.length === 10) p.reported_at = p.reported_at + 'T09:00:00'; return p }

const act = async (row, action, reload) => {
    try { await bcmApi.incidents[action](row.id); toast.add({ severity: 'success', summary: 'Updated', life: 2500 }); reload() }
    catch (e) { toast.add({ severity: 'error', summary: 'Not allowed', detail: page.value.errorMessage(e), life: 5000 }) }
}
const resolveVisible = ref(false)
const busy = ref(false)
const resolveForm = reactive({ row: null, lessons: '', reload: null })
const openResolve = (row, reload) => { Object.assign(resolveForm, { row, lessons: row.lessons_learned || '', reload }); resolveVisible.value = true }
const submitResolve = async () => {
    busy.value = true
    try { await bcmApi.incidents.resolve(resolveForm.row.id, resolveForm.lessons); resolveVisible.value = false; resolveForm.reload() }
    catch (e) { toast.add({ severity: 'error', summary: 'Not allowed', detail: page.value.errorMessage(e), life: 5000 }) }
    finally { busy.value = false }
}

onMounted(async () => {
    const orgId = await appStore.ensureOrganization()
    const p = { organization: orgId, page_size: 500 }
    const [risks, fns, users, bc, dr, teams] = await Promise.all([
        riskApi.risks.list(p), bcmApi.functions.list(p), coreApi.users.list({ page_size: 500 }),
        bcmApi.plans.list(p), bcmApi.drPlans.list(p), bcmApi.crisisTeams.list(p)])
    const rows = (r) => r.data.results || r.data
    lookups.risks = rows(risks).map(r => ({ label: `${r.risk_id} - ${r.title}`, value: r.id }))
    lookups.functions = rows(fns).map(f => ({ label: `${f.function_id} - ${f.name}`, value: f.id }))
    lookups.users = rows(users).map(u => ({ label: u.full_name || u.username, value: u.id }))
    lookups.bcPlans = rows(bc).map(x => ({ label: `${x.plan_id} - ${x.title}`, value: x.id }))
    lookups.drPlans = rows(dr).map(x => ({ label: `${x.plan_id} - ${x.title}`, value: x.id }))
    lookups.teams = rows(teams).map(x => ({ label: x.name, value: x.id }))
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
