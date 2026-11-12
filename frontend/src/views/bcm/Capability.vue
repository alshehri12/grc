<template>
    <div class="capability-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('bcm.capability') }}</h1>
                <p>تحليل قدرة التعافي - What the business needs (BIA) vs. what IT can deliver (DR plans) and what exercises have proven</p>
            </div>
            <div class="header-actions">
                <SelectButton v-model="scope" :options="scopeOptions" optionLabel="label" optionValue="value" @change="load" />
                <Button icon="pi pi-refresh" text @click="load" :loading="loading" />
            </div>
        </div>

        <div class="stats-grid" v-if="report">
            <div class="stat-card covered"><span class="stat-value">{{ report.summary.covered }}</span><span class="stat-label">Recoverable & proven</span></div>
            <div class="stat-card amber"><span class="stat-value">{{ report.summary.untested + report.summary.unproven }}</span><span class="stat-label">Not proven by exercise</span></div>
            <div class="stat-card red"><span class="stat-value">{{ report.summary.gap + report.summary.no_dr_plan }}</span><span class="stat-label">Capability gap / no DR plan</span></div>
            <div class="stat-card"><span class="stat-value">{{ report.summary.no_bia + report.summary.no_dependencies }}</span><span class="stat-label">Missing BIA / dependencies</span></div>
            <div class="stat-card critical"><span class="stat-value">{{ report.summary.critical_at_risk }}</span><span class="stat-label">Critical/essential at risk</span></div>
        </div>

        <Card>
            <template #content>
                <DataTable :value="report?.functions || []" :loading="loading" v-model:expandedRows="expanded" dataKey="function.id" responsiveLayout="scroll" sortField="statusRank" :sortOrder="1">
                    <Column expander style="width: 3rem" />
                    <Column field="function.function_id" header="ID" style="width: 90px" />
                    <Column header="Business function" sortable field="function.name">
                        <template #body="{ data }"><div>{{ data.function.name }}</div><div class="text-muted">{{ data.function.name_ar }} · {{ data.function.owner || '-' }}</div></template>
                    </Column>
                    <Column field="function.criticality" header="Criticality" sortable><template #body="{ data }"><Tag :severity="critSev[data.function.criticality]">{{ data.function.criticality }}</Tag></template></Column>
                    <Column header="Required RTO / RPO"><template #body="{ data }">{{ h(data.required?.rto_hours) }} / {{ h(data.required?.rpo_hours) }} <small class="text-muted" v-if="data.required">(MTPD {{ h(data.required.mtpd_hours) }})</small></template></Column>
                    <Column header="Achievable RTO / RPO"><template #body="{ data }"><span :class="{ bad: data.achievable?.rto_hours > data.required?.rto_hours }">{{ h(data.achievable?.rto_hours) }}</span> / <span :class="{ bad: data.achievable?.rpo_hours > data.required?.rpo_hours }">{{ h(data.achievable?.rpo_hours) }}</span></template></Column>
                    <Column header="Proven by exercise"><template #body="{ data }"><span v-if="data.proven?.rto_hours != null" :class="{ bad: data.proven.rto_hours > data.required?.rto_hours }">{{ data.proven.rto_hours }}h</span><span v-else class="text-muted">-</span><small v-if="data.proven && !data.proven.recent" class="text-muted"> (stale)</small></template></Column>
                    <Column header="Status" sortable field="status"><template #body="{ data }"><span class="rag" :class="data.status">{{ statusLabel[data.status] }}</span></template></Column>
                    <template #expansion="{ data }">
                        <div class="expansion">
                            <div v-if="data.issues?.length"><b>Issues</b><ul class="issue-list"><li v-for="(i, idx) in data.issues" :key="idx">{{ i }}</li></ul></div>
                            <DataTable :value="data.assets" size="small" v-if="data.assets?.length" class="mt">
                                <Column field="asset_id" header="System" style="width: 110px" />
                                <Column field="name" header="Name" />
                                <Column header="DR plans"><template #body="{ data: a }">
                                    <div v-for="p in a.plans" :key="p.id">{{ p.plan_id }} - {{ p.title }} <small class="text-muted">(RTO {{ h(p.achievable_rto_hours) }}, RPO {{ h(p.achievable_rpo_hours) }}, next test {{ p.next_test_date || '-' }})</small></div>
                                    <span v-if="!a.plans.length" class="rag no_dr_plan">no DR plan</span>
                                </template></Column>
                                <Column header="Last measured exercise"><template #body="{ data: a }">
                                    <div v-for="p in a.plans.filter(x => x.last_test)" :key="p.id">{{ p.last_test.test_id }}: {{ p.last_test.achieved_rto_hours }}h on {{ String(p.last_test.date).slice(0, 10) }} <span class="rag" :class="p.last_test.result">{{ p.last_test.result || '-' }}</span></div>
                                </template></Column>
                                <Column header="Status" style="width: 120px"><template #body="{ data: a }"><span class="rag" :class="a.status">{{ statusLabel[a.status] }}</span></template></Column>
                            </DataTable>
                            <div class="mt"><Button size="small" text icon="pi pi-shield" label="Threat profile" @click="showThreats(data)" /></div>
                        </div>
                    </template>
                </DataTable>
                <p class="text-muted" style="margin-top:.75rem">
                    Status logic: <b>covered</b> = achievable RTO/RPO within the BIA requirement and proven by an exercise in the last 12 months;
                    <b>untested</b> = requirement met on paper only; <b>unproven</b> = last exercise missed the RTO; <b>gap</b> = plan cannot meet the requirement;
                    <b>no DR plan</b> = a dependent system has no approved DR plan. The weekly automation notifies function and plan owners of every non-covered critical function.
                </p>
            </template>
        </Card>

        <Dialog v-model:visible="threatVisible" :header="`Threat profile - ${threats?.function?.name || ''}`" modal :style="{ width: '860px' }">
            <div v-if="threats">
                <div class="stats-grid">
                    <div class="stat-card critical"><span class="stat-value">{{ threats.summary.by_level.critical }}</span><span class="stat-label">Critical</span></div>
                    <div class="stat-card high"><span class="stat-value">{{ threats.summary.by_level.high }}</span><span class="stat-label">High</span></div>
                    <div class="stat-card medium"><span class="stat-value">{{ threats.summary.by_level.medium }}</span><span class="stat-label">Medium</span></div>
                    <div class="stat-card breach"><span class="stat-value">{{ threats.summary.outside_appetite }}</span><span class="stat-label">Outside appetite</span></div>
                </div>
                <DataTable :value="threats.risks" size="small">
                    <Column field="risk_id" header="ID" /><Column field="title" header="Risk" /><Column field="risk_type" header="Type" />
                    <Column header="Inherent → Residual"><template #body="{ data }"><span class="risk-score" :class="data.inherent_level">{{ data.inherent_score }}</span> → <span class="risk-score" :class="data.residual_level || data.inherent_level">{{ data.residual_score ?? '-' }}</span></template></Column>
                    <Column header="Appetite"><template #body="{ data }"><span class="rag" :class="data.appetite_status">{{ data.appetite_status }}</span></template></Column>
                    <Column field="incidents_12m" header="Incidents 12m" /><Column header="Link"><template #body="{ data }">{{ data.direct ? 'direct' : 'via asset' }}</template></Column>
                </DataTable>
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
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import SelectButton from 'primevue/selectbutton'
import { bcmApi } from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const report = ref(null)
const loading = ref(false)
const expanded = ref([])
const scope = ref('critical,essential')
const scopeOptions = [{ label: 'Critical & essential', value: 'critical,essential' }, { label: 'All functions', value: '' }]
const critSev = { critical: 'danger', essential: 'warn', necessary: 'info', desirable: 'secondary' }
const statusLabel = { covered: 'COVERED', untested: 'UNTESTED', unproven: 'UNPROVEN', gap: 'GAP', no_dr_plan: 'NO DR PLAN', no_bia: 'NO BIA', no_dependencies: 'NO DEPENDENCIES' }
const rank = { no_dr_plan: 0, gap: 1, unproven: 2, untested: 3, no_bia: 4, no_dependencies: 5, covered: 6 }
const h = (v) => v == null ? '-' : `${v}h`
const threatVisible = ref(false)
const threats = ref(null)

const load = async () => {
    loading.value = true
    try {
        const orgId = await appStore.ensureOrganization()
        const res = await bcmApi.functions.capabilityAnalysis(orgId, scope.value || undefined)
        res.data.functions.forEach(f => { f.statusRank = rank[f.status] })
        report.value = res.data
    } finally { loading.value = false }
}
const showThreats = async (row) => { threats.value = (await bcmApi.functions.threatProfile(row.function.id)).data; threatVisible.value = true }
onMounted(load)
</script>

<style scoped src="@/assets/grc-pages.css"></style>
<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.25rem; }
.page-header h1 { margin: 0 0 .25rem; } .page-header p { margin: 0; color: var(--p-text-muted-color); }
.header-actions { display: flex; gap: .5rem; align-items: center; }
.expansion { padding: .5rem 1rem 1rem 3rem; background: var(--p-surface-50); }
.dark-mode .expansion { background: var(--p-surface-800); }
.bad { color: #dc2626; font-weight: 700; }
.mt { margin-top: .75rem; }
</style>
