<template>
    <div>
        <CrudPage ref="page" :title="$t('risk.appetite')" subtitle="شهية المخاطر وحدود التحمل - Risk Appetite & Tolerance"
                  :api="riskApi.appetites" :columns="columns" :fields="fields" :lookups="lookups" itemLabel="appetite statement"
                  titleField="statement" :canCreate="authStore.canApprove" :editable="authStore.canApprove" :deletable="authStore.isAdmin"
                  :defaults="{ max_acceptable_score: 12, tolerance_score: 16, is_active: true }" :transformIn="inn" @loaded="loadExposure">
            <template #above-table>
                <div class="stats-grid" v-if="exposure">
                    <div class="stat-card within"><span class="stat-value">{{ exposure.counts.within }}</span><span class="stat-label">Within appetite</span></div>
                    <div class="stat-card tolerance"><span class="stat-value">{{ exposure.counts.tolerance }}</span><span class="stat-label">Outside appetite (treatment required)</span></div>
                    <div class="stat-card breach"><span class="stat-value">{{ exposure.counts.breach }}</span><span class="stat-label">Above tolerance (escalated)</span></div>
                </div>
            </template>
            <template #col-category_name="{ data }">{{ data.category_name || 'Organization-wide default' }}</template>
            <template #col-risks_outside="{ data }"><span class="rag" :class="data.risks_outside ? 'red' : 'green'">{{ data.risks_outside }}</span></template>
            <template #view="{ data }">
                <div class="detail-grid" v-if="data">
                    <div><b>Scope</b><div>{{ data.category_name || 'Organization-wide default' }}</div></div>
                    <div><b>Appetite / Tolerance</b><div>≤ {{ data.max_acceptable_score }} / ≤ {{ data.tolerance_score }}</div></div>
                    <div><b>Approved by</b><div>{{ data.approved_by_name || '-' }} {{ data.approved_date ? '(' + data.approved_date + ')' : '' }}</div></div>
                    <div><b>Review date</b><div>{{ data.review_date || '-' }}</div></div>
                    <div class="full"><b>Statement</b><div>{{ data.statement }}</div></div>
                    <div class="full" v-if="data.statement_ar"><b>البيان</b><div dir="rtl">{{ data.statement_ar }}</div></div>
                </div>
            </template>
        </CrudPage>

        <Card class="mt" v-if="exposure">
            <template #title>Risks outside appetite ({{ exposure.outside_appetite.length }})</template>
            <template #content>
                <DataTable :value="exposure.outside_appetite" responsiveLayout="scroll" paginator :rows="10">
                    <Column field="risk_id" header="ID" style="width: 130px" />
                    <Column field="title" header="Risk" />
                    <Column field="category" header="Category" />
                    <Column header="Exposure"><template #body="{ data }"><span class="risk-score" :class="lvl(data.score)">{{ data.score }}</span> <small class="text-muted">({{ data.basis }})</small></template></Column>
                    <Column header="Appetite / Tolerance"><template #body="{ data }">{{ data.appetite }} / {{ data.tolerance }}</template></Column>
                    <Column header="Status"><template #body="{ data }"><span class="rag" :class="data.status">{{ data.status === 'breach' ? 'ABOVE TOLERANCE' : 'OUTSIDE APPETITE' }}</span></template></Column>
                    <Column field="active_treatments" header="Active treatments" />
                    <Column field="owner" header="Owner" />
                </DataTable>
                <p class="text-muted" style="margin-top:.75rem">The automation checks this daily: owners and department managers are notified, a treatment task is created when no treatment is active, and risks above tolerance are escalated to the next management level.</p>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import CrudPage from '@/components/CrudPage.vue'
import { riskApi, coreApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const appStore = useAppStore()
const authStore = useAuthStore()
const page = ref(null)
const exposure = ref(null)
const lookups = reactive({ categories: [], users: [] })
const thresholds = ref({ medium: 6, high: 12, critical: 20 })
const lvl = (s) => s >= thresholds.value.critical ? 'critical' : s >= thresholds.value.high ? 'high' : s >= thresholds.value.medium ? 'medium' : 'low'

const columns = [
    { field: 'category_name', header: 'Scope' },
    { field: 'statement', header: 'Statement', style: 'min-width: 320px' },
    { field: 'max_acceptable_score', header: 'Appetite ≤', style: 'width: 110px' },
    { field: 'tolerance_score', header: 'Tolerance ≤', style: 'width: 110px' },
    { field: 'risks_outside', header: 'Risks outside', style: 'width: 120px' },
    { field: 'review_date', header: 'Review', type: 'date' },
    { field: 'is_active', header: 'Active', type: 'bool', style: 'width: 80px' },
]
const fields = [
    { name: 'category', label: 'Risk category (empty = organization-wide default)', type: 'select', optionsKey: 'categories', full: true },
    { name: 'statement', label: 'Appetite statement', type: 'textarea', required: true, rows: 3 },
    { name: 'statement_ar', label: 'بيان شهية المخاطر', type: 'textarea', dir: 'rtl' },
    { name: 'max_acceptable_score', label: 'Appetite: max acceptable residual score (1-25)', type: 'number', min: 1, max: 25, required: true },
    { name: 'tolerance_score', label: 'Tolerance: escalation score (1-25)', type: 'number', min: 1, max: 25, required: true },
    { name: 'approved_by', label: 'Approved by', type: 'select', optionsKey: 'users' },
    { name: 'approved_date', label: 'Approved date', type: 'date' },
    { name: 'effective_from', label: 'Effective from', type: 'date' },
    { name: 'review_date', label: 'Next review date', type: 'date' },
    { name: 'is_active', label: 'Active', type: 'switch' },
]
const inn = (r) => ({ ...r, approved_date: r.approved_date ? new Date(r.approved_date) : null, effective_from: r.effective_from ? new Date(r.effective_from) : null, review_date: r.review_date ? new Date(r.review_date) : null })

const loadExposure = async () => {
    const orgId = await appStore.ensureOrganization()
    const [exp, cfg] = await Promise.all([riskApi.appetites.exposure(orgId), riskApi.risks.matrixConfig(orgId)])
    exposure.value = exp.data
    thresholds.value = cfg.data.thresholds
}

onMounted(async () => {
    const [cats, users] = await Promise.all([riskApi.categories.list(), coreApi.users.list({ page_size: 500 })])
    lookups.categories = (cats.data.results || cats.data).map(c => ({ label: c.name, value: c.id }))
    lookups.users = (users.data.results || users.data).map(u => ({ label: u.full_name || u.username, value: u.id }))
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
<style scoped>.mt { margin-top: 1.25rem; }</style>
