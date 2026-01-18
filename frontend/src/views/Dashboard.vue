<template>
    <div class="dashboard">
        <div class="dashboard-header">
            <h1>{{ $t('dashboard.title') }}</h1>
            <p class="welcome-text">
                {{ $t('dashboard.welcome') }}, {{ authStore.userFullName }}
            </p>
        </div>
        
        <!-- KPI Cards Row 1 -->
        <div class="kpi-grid">
            <div class="kpi-card risk">
                <div class="kpi-icon">
                    <i class="pi pi-exclamation-triangle"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.risks?.total || 0 }}</span>
                    <span class="kpi-label">{{ $t('dashboard.totalRisks') }}</span>
                </div>
                <div class="kpi-badge critical" v-if="summary.risks?.critical > 0">
                    {{ summary.risks.critical }} {{ $t('status.critical') }}
                </div>
            </div>
            
            <div class="kpi-card compliance">
                <div class="kpi-icon">
                    <i class="pi pi-check-circle"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.compliance?.compliance_rate || 0 }}%</span>
                    <span class="kpi-label">{{ $t('dashboard.complianceScore') }}</span>
                </div>
            </div>
            
            <div class="kpi-card policies">
                <div class="kpi-icon">
                    <i class="pi pi-file"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.policies?.total || 0 }}</span>
                    <span class="kpi-label">{{ $t('governance.policies') }}</span>
                </div>
                <div class="kpi-badge warning" v-if="summary.policies?.expiring_soon > 0">
                    {{ summary.policies.expiring_soon }} Expiring
                </div>
            </div>
            
            <div class="kpi-card findings">
                <div class="kpi-icon">
                    <i class="pi pi-flag"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.findings?.total_open || 0 }}</span>
                    <span class="kpi-label">{{ $t('dashboard.openFindings') }}</span>
                </div>
                <div class="kpi-badge critical" v-if="summary.findings?.overdue > 0">
                    {{ summary.findings.overdue }} Overdue
                </div>
            </div>
        </div>
        
        <!-- KPI Cards Row 2 - BCM -->
        <div class="kpi-grid">
            <div class="kpi-card bcm">
                <div class="kpi-icon">
                    <i class="pi pi-shield"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.bcm?.bc_plans || 0 }}</span>
                    <span class="kpi-label">{{ $t('bcm.bcp') }}</span>
                </div>
                <div class="kpi-badge success" v-if="summary.bcm?.bc_plans_active > 0">
                    {{ summary.bcm.bc_plans_active }} Active
                </div>
            </div>
            
            <div class="kpi-card drp">
                <div class="kpi-icon">
                    <i class="pi pi-server"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.bcm?.dr_plans || 0 }}</span>
                    <span class="kpi-label">{{ $t('bcm.drp') }}</span>
                </div>
            </div>
            
            <div class="kpi-card functions">
                <div class="kpi-icon">
                    <i class="pi pi-sitemap"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.bcm?.business_functions || 0 }}</span>
                    <span class="kpi-label">{{ $t('bcm.functions') }}</span>
                </div>
                <div class="kpi-badge critical" v-if="summary.bcm?.critical_functions > 0">
                    {{ summary.bcm.critical_functions }} Critical
                </div>
            </div>
            
            <div class="kpi-card tasks">
                <div class="kpi-icon">
                    <i class="pi pi-list-check"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.tasks?.pending || 0 }}</span>
                    <span class="kpi-label">{{ $t('dashboard.pendingTasks') }}</span>
                </div>
                <div class="kpi-badge warning" v-if="summary.tasks?.overdue > 0">
                    {{ summary.tasks.overdue }} Overdue
                </div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div class="charts-row">
            <Card class="chart-card">
                <template #title>{{ $t('dashboard.riskOverview') }}</template>
                <template #content>
                    <Chart type="doughnut" :data="riskChartData" :options="chartOptions" />
                </template>
            </Card>
            
            <Card class="chart-card">
                <template #title>{{ $t('dashboard.complianceStatus') }}</template>
                <template #content>
                    <Chart type="bar" :data="complianceChartData" :options="barChartOptions" />
                </template>
            </Card>
            
            <Card class="chart-card">
                <template #title>{{ $t('bcm.title') }}</template>
                <template #content>
                    <Chart type="pie" :data="bcmChartData" :options="chartOptions" />
                </template>
            </Card>
        </div>
        
        <!-- Tables Row -->
        <div class="tables-row">
            <Card class="table-card">
                <template #title>{{ $t('dashboard.pendingTasks') }}</template>
                <template #content>
                    <DataTable :value="tasks" :rows="5" paginator responsiveLayout="scroll">
                        <template #empty>
                            <div class="empty-state">
                                <i class="pi pi-check-circle"></i>
                                <p>No pending tasks</p>
                            </div>
                        </template>
                        <Column field="title" :header="$t('common.title')"></Column>
                        <Column field="priority" :header="$t('common.priority')">
                            <template #body="{ data }">
                                <Tag :severity="getPrioritySeverity(data.priority)">
                                    {{ data.priority }}
                                </Tag>
                            </template>
                        </Column>
                        <Column field="due_date" header="Due Date"></Column>
                    </DataTable>
                </template>
            </Card>
            
            <Card class="table-card">
                <template #title>{{ $t('dashboard.upcomingAudits') }}</template>
                <template #content>
                    <DataTable :value="audits" :rows="5" paginator responsiveLayout="scroll">
                        <template #empty>
                            <div class="empty-state">
                                <i class="pi pi-calendar"></i>
                                <p>No upcoming audits</p>
                            </div>
                        </template>
                        <Column field="title" :header="$t('common.title')"></Column>
                        <Column field="audit_type" :header="$t('common.type')"></Column>
                        <Column field="planned_start_date" header="Start Date"></Column>
                    </DataTable>
                </template>
            </Card>
        </div>
        
        <!-- Quick Stats Summary -->
        <Card class="summary-card">
            <template #title>GRC Summary</template>
            <template #content>
                <div class="summary-grid">
                    <div class="summary-item">
                        <span class="summary-label">{{ $t('governance.policies') }}</span>
                        <span class="summary-value">{{ summary.policies?.total || 0 }}</span>
                        <span class="summary-sub">{{ summary.policies?.published || 0 }} published</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{{ $t('risk.register') }}</span>
                        <span class="summary-value">{{ summary.risks?.total || 0 }}</span>
                        <span class="summary-sub">{{ summary.risks?.treating || 0 }} under treatment</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{{ $t('compliance.controls') }}</span>
                        <span class="summary-value">{{ summary.compliance?.total_controls || 0 }}</span>
                        <span class="summary-sub">{{ summary.compliance?.implemented || 0 }} implemented</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{{ $t('compliance.audits') }}</span>
                        <span class="summary-value">{{ summary.audits?.total || 0 }}</span>
                        <span class="summary-sub">{{ summary.audits?.completed || 0 }} completed</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">{{ $t('bcm.bcp') }}</span>
                        <span class="summary-value">{{ summary.bcm?.bc_plans || 0 }}</span>
                        <span class="summary-sub">{{ summary.bcm?.bc_plans_active || 0 }} active</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">BCM Tests</span>
                        <span class="summary-value">{{ summary.bcm?.tests_completed || 0 }}</span>
                        <span class="summary-sub">{{ summary.bcm?.tests_planned || 0 }} planned</span>
                    </div>
                </div>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import Card from 'primevue/card'
import Chart from 'primevue/chart'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { dashboardApi, workflowApi, complianceApi } from '@/api'

const authStore = useAuthStore()
const appStore = useAppStore()

const summary = ref({})
const tasks = ref([])
const audits = ref([])

const riskChartData = computed(() => ({
    labels: ['Critical', 'High', 'Medium', 'Low'],
    datasets: [{
        data: [
            summary.value.risks?.by_level?.critical || 0,
            summary.value.risks?.by_level?.high || 0,
            summary.value.risks?.by_level?.medium || 0,
            summary.value.risks?.by_level?.low || 0
        ],
        backgroundColor: ['#dc2626', '#ea580c', '#ca8a04', '#16a34a']
    }]
}))

const complianceChartData = computed(() => ({
    labels: ['Implemented', 'Partial', 'Not Implemented'],
    datasets: [{
        label: 'Controls',
        data: [
            summary.value.compliance?.implemented || 0,
            summary.value.compliance?.partial || 0,
            summary.value.compliance?.not_implemented || 0
        ],
        backgroundColor: ['#16a34a', '#ca8a04', '#dc2626']
    }]
}))

const bcmChartData = computed(() => ({
    labels: ['BC Plans', 'DR Plans', 'Business Functions'],
    datasets: [{
        data: [
            summary.value.bcm?.bc_plans || 0,
            summary.value.bcm?.dr_plans || 0,
            summary.value.bcm?.business_functions || 0
        ],
        backgroundColor: ['#0891b2', '#7c3aed', '#0d9488']
    }]
}))

const chartOptions = {
    plugins: {
        legend: {
            position: 'bottom'
        }
    },
    responsive: true,
    maintainAspectRatio: false
}

const barChartOptions = {
    ...chartOptions,
    scales: {
        y: {
            beginAtZero: true
        }
    }
}

const getPrioritySeverity = (priority) => {
    const map = {
        critical: 'danger',
        high: 'warn',
        medium: 'info',
        low: 'success'
    }
    return map[priority] || 'info'
}

onMounted(async () => {
    try {
        // Fetch executive summary
        const orgId = appStore.currentOrganization?.id || 1
        const summaryRes = await dashboardApi.executiveSummary(orgId)
        summary.value = summaryRes.data
        
        // Fetch my tasks
        const tasksRes = await workflowApi.tasks.myTasks()
        tasks.value = tasksRes.data || []
        
        // Fetch upcoming audits
        const auditsRes = await complianceApi.audits.list({ status: 'planned' })
        audits.value = auditsRes.data.results || auditsRes.data || []
    } catch (error) {
        console.error('Failed to load dashboard data:', error)
    }
})
</script>

<style scoped>
.dashboard {
    max-width: 1400px;
    margin: 0 auto;
}

.dashboard-header {
    margin-bottom: 2rem;
}

.dashboard-header h1 {
    margin: 0 0 0.5rem;
    font-size: 1.75rem;
    font-weight: 700;
}

.welcome-text {
    color: var(--p-text-muted-color);
    margin: 0;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.kpi-card {
    background: var(--p-surface-0);
    border-radius: 12px;
    padding: 1.25rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    position: relative;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    border-left: 4px solid;
}

.kpi-icon {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
}

.kpi-card.risk { border-color: #dc2626; }
.kpi-card.risk .kpi-icon { background: rgba(220, 38, 38, 0.1); color: #dc2626; }

.kpi-card.compliance { border-color: #16a34a; }
.kpi-card.compliance .kpi-icon { background: rgba(22, 163, 74, 0.1); color: #16a34a; }

.kpi-card.policies { border-color: #2563eb; }
.kpi-card.policies .kpi-icon { background: rgba(37, 99, 235, 0.1); color: #2563eb; }

.kpi-card.findings { border-color: #ea580c; }
.kpi-card.findings .kpi-icon { background: rgba(234, 88, 12, 0.1); color: #ea580c; }

.kpi-card.bcm { border-color: #0891b2; }
.kpi-card.bcm .kpi-icon { background: rgba(8, 145, 178, 0.1); color: #0891b2; }

.kpi-card.drp { border-color: #7c3aed; }
.kpi-card.drp .kpi-icon { background: rgba(124, 58, 237, 0.1); color: #7c3aed; }

.kpi-card.functions { border-color: #0d9488; }
.kpi-card.functions .kpi-icon { background: rgba(13, 148, 136, 0.1); color: #0d9488; }

.kpi-card.tasks { border-color: #ca8a04; }
.kpi-card.tasks .kpi-icon { background: rgba(202, 138, 4, 0.1); color: #ca8a04; }

.kpi-content {
    display: flex;
    flex-direction: column;
}

.kpi-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--p-text-color);
}

.kpi-label {
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
}

.kpi-badge {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
}

:dir(rtl) .kpi-badge {
    right: auto;
    left: 0.75rem;
}

.kpi-badge.critical { background: rgba(220, 38, 38, 0.1); color: #dc2626; }
.kpi-badge.warning { background: rgba(234, 88, 12, 0.1); color: #ea580c; }
.kpi-badge.success { background: rgba(22, 163, 74, 0.1); color: #16a34a; }

.charts-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}

.tables-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}

.chart-card :deep(.p-card-content) {
    height: 280px;
}

.table-card :deep(.p-datatable) {
    font-size: 0.9rem;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 2rem;
    color: var(--p-text-muted-color);
}

.empty-state i {
    font-size: 2rem;
}

.summary-card {
    margin-bottom: 1.5rem;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1.5rem;
}

.summary-item {
    text-align: center;
    padding: 1rem;
    background: var(--p-surface-100);
    border-radius: 8px;
}

.summary-label {
    display: block;
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
    margin-bottom: 0.5rem;
}

.summary-value {
    display: block;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--p-text-color);
}

.summary-sub {
    display: block;
    font-size: 0.75rem;
    color: var(--p-text-muted-color);
    margin-top: 0.25rem;
}

/* Dark mode */
.dark-mode .kpi-card {
    background: var(--p-surface-800);
}

.dark-mode .summary-item {
    background: var(--p-surface-700);
}
</style>
