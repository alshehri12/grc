<template>
    <CrudPage ref="page" :title="$t('risk.acceptances')" subtitle="قبول المخاطر - Risk Acceptance Requests"
              :api="riskApi.acceptances" :columns="columns" :fields="fields" :lookups="lookups" :orgScoped="false"
              itemLabel="acceptance request" titleField="risk_title" :defaults="{ status: 'pending' }"
              :editable="(r) => r.status === 'pending'" :deletable="(r) => r.status === 'pending'" :transformOut="out" :transformIn="inn">
        <template #above-table="{ rows }">
            <div class="stats-grid">
                <div class="stat-card medium"><span class="stat-value">{{ count(rows, 'pending') }}</span><span class="stat-label">Pending decision</span></div>
                <div class="stat-card low"><span class="stat-value">{{ count(rows, 'approved') }}</span><span class="stat-label">Approved (in force)</span></div>
                <div class="stat-card critical"><span class="stat-value">{{ count(rows, 'expired') }}</span><span class="stat-label">Expired - re-assess</span></div>
                <div class="stat-card"><span class="stat-value">{{ count(rows, 'rejected') }}</span><span class="stat-label">Rejected</span></div>
            </div>
        </template>
        <template #row-actions="{ data, reload }">
            <template v-if="data.status === 'pending' && authStore.canApprove">
                <Button icon="pi pi-check" text rounded severity="success" v-tooltip="$t('common.approve')" @click="decide(data, 'approve', reload)" />
                <Button icon="pi pi-times" text rounded severity="danger" v-tooltip="$t('common.reject')" @click="decide(data, 'reject', reload)" />
            </template>
        </template>
        <template #view="{ data }">
            <div class="detail-grid" v-if="data">
                <div><b>Risk</b><div>{{ data.risk_title }}</div></div>
                <div><b>Status</b><div><Tag :severity="sev[data.status]">{{ data.status }}</Tag></div></div>
                <div><b>Accepted score</b><div>{{ data.accepted_likelihood }} × {{ data.accepted_impact }} = {{ data.accepted_risk_score }}</div></div>
                <div><b>Valid</b><div>{{ data.valid_from }} → {{ data.valid_until }}</div></div>
                <div><b>Requested by</b><div>{{ data.requested_by_name || '-' }} ({{ data.requested_date }})</div></div>
                <div><b>Decided by</b><div>{{ data.approved_by_name || '-' }} {{ data.approved_date ? '(' + data.approved_date + ')' : '' }}</div></div>
                <div class="full"><b>Justification</b><div>{{ data.justification }}</div></div>
                <div class="full" v-if="data.conditions"><b>Conditions</b><div>{{ data.conditions }}</div></div>
                <div class="full" v-if="data.approval_comments"><b>Decision comments</b><div>{{ data.approval_comments }}</div></div>
            </div>
        </template>
    </CrudPage>

    <Dialog v-model:visible="decisionVisible" :header="decision.action === 'approve' ? 'Approve acceptance' : 'Reject acceptance'" modal :style="{ width: '460px' }">
        <p class="text-muted">Acceptance decisions are recorded in the audit trail. The requester cannot decide their own request.</p>
        <div class="form-field"><label>Comments <span v-if="decision.action === 'reject'" style="color:#dc2626">*</span></label><Textarea v-model="decision.comments" rows="3" autoResize /></div>
        <template #footer>
            <Button :label="$t('common.cancel')" text @click="decisionVisible = false" />
            <Button :label="decision.action === 'approve' ? $t('common.approve') : $t('common.reject')" :severity="decision.action === 'approve' ? 'success' : 'danger'" @click="submitDecision" :loading="deciding" />
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
import { riskApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const appStore = useAppStore()
const authStore = useAuthStore()
const toast = useToast()
const page = ref(null)
const lookups = reactive({ risks: [] })
const sev = { pending: 'warn', approved: 'success', rejected: 'danger', expired: 'secondary' }
const count = (rows, s) => rows.filter(r => r.status === s).length
const scale = [1, 2, 3, 4, 5].map(v => ({ label: String(v), value: v }))

const columns = [
    { field: 'risk_title', header: 'Risk', style: 'min-width: 240px' },
    { field: 'accepted_risk_score', header: 'Accepted score', style: 'width: 120px' },
    { field: 'status', header: 'Status', type: 'tag', severities: sev },
    { field: 'valid_until', header: 'Valid until', type: 'date' },
    { field: 'requested_by_name', header: 'Requested by' },
    { field: 'approved_by_name', header: 'Decided by' },
]
const fields = [
    { name: 'risk', label: 'Risk', type: 'select', optionsKey: 'risks', required: true, full: true },
    { name: 'justification', label: 'Justification (why accepting is appropriate)', type: 'textarea', required: true },
    { name: 'conditions', label: 'Conditions / compensating measures', type: 'textarea' },
    { name: 'accepted_likelihood', label: 'Accepted likelihood (1-5)', type: 'select', options: scale, required: true },
    { name: 'accepted_impact', label: 'Accepted impact (1-5)', type: 'select', options: scale, required: true },
    { name: 'valid_from', label: 'Valid from', type: 'date', required: true },
    { name: 'valid_until', label: 'Valid until', type: 'date', required: true, help: 'Expired acceptances are flagged automatically and must be re-assessed.' },
]
const out = (p) => { delete p.organization; delete p.status; return p }
const inn = (r) => ({ ...r, valid_from: r.valid_from ? new Date(r.valid_from) : null, valid_until: r.valid_until ? new Date(r.valid_until) : null })

const decisionVisible = ref(false)
const deciding = ref(false)
const decision = reactive({ row: null, action: 'approve', comments: '', reload: null })
const decide = (row, action, reload) => { Object.assign(decision, { row, action, comments: '', reload }); decisionVisible.value = true }
const submitDecision = async () => {
    if (decision.action === 'reject' && !decision.comments.trim()) {
        toast.add({ severity: 'warn', summary: 'Reason required', life: 3000 }); return
    }
    deciding.value = true
    try {
        await riskApi.acceptances[decision.action](decision.row.id, decision.comments)
        toast.add({ severity: 'success', summary: decision.action === 'approve' ? 'Approved' : 'Rejected', life: 2500 })
        decisionVisible.value = false
        decision.reload()
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Not allowed', detail: page.value.errorMessage(e), life: 5000 })
    } finally { deciding.value = false }
}

onMounted(async () => {
    const orgId = await appStore.ensureOrganization()
    const risks = await riskApi.risks.list({ organization: orgId, page_size: 500 })
    lookups.risks = (risks.data.results || risks.data).map(r => ({ label: `${r.risk_id} - ${r.title}`, value: r.id }))
})
</script>

<style scoped src="@/assets/grc-pages.css"></style>
