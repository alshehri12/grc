<template>
    <div class="dashboard">
        <div class="dashboard-header">
            <h1>{{ $t('dashboard.title') }}</h1>
            <p class="welcome-text">
                {{ $t('dashboard.welcome') }}, {{ authStore.userFullName }}
            </p>
        </div>
        
        <!-- KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card risk">
                <div class="kpi-icon">
                    <i class="pi pi-exclamation-triangle"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.risks?.total || 0 }}</span>
                    <span class="kpi-label">{{ $t('risk.register') }}</span>
                </div>
                <div class="kpi-badge critical" v-if="summary.risks?.critical > 0">
                    {{ summary.risks.critical }} Critical
                </div>
            </div>
            
            <div class="kpi-card compliance">
                <div class="kpi-icon">
                    <i class="pi pi-check-circle"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.compliance?.compliance_rate || 0 }}%</span>
                    <span class="kpi-label">{{ $t('dashboard.complianceStatus') }}</span>
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
            
            <div class="kpi-card findings">
                <div class="kpi-icon">
                    <i class="pi pi-flag"></i>
                </div>
                <div class="kpi-content">
                    <span class="kpi-value">{{ summary.findings?.total_open || 0 }}</span>
                    <span class="kpi-label">Open Findings</span>
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
        </div>
        
        <!-- Tables Row -->
        <div class="tables-row">
            <Card class="table-card">
                <template #title>{{ $t('dashboard.pendingTasks') }}</template>
                <template #content>
                    <DataTable :value="tasks" :rows="5" paginator responsiveLayout="scroll">
                        <Column field="title" :header="$t('common.status')"></Column>
                        <Column field="priority" header="Priority">
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
                        <Column field="title" header="Audit"></Column>
                        <Column field="audit_type" header="Type"></Column>
                        <Column field="planned_start_date" header="Start Date"></Column>
                    </DataTable>
                </template>
            </Card>
        </div>
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
            Math.round((summary.value.compliance?.total_controls || 0) * 0.2),
            Math.round((summary.value.compliance?.total_controls || 0) * 0.2)
        ],
        backgroundColor: ['#16a34a', '#ca8a04', '#dc2626']
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
        const orgId = appStore.currentOrganization?.id
        if (orgId) {
            const summaryRes = await dashboardApi.executiveSummary(orgId)
            summary.value = summaryRes.data
        }
        
        // Fetch my tasks
        const tasksRes = await workflowApi.tasks.myTasks()
        tasks.value = tasksRes.data
        
        // Fetch upcoming audits
        const auditsRes = await complianceApi.audits.list({ status: 'planned' })
        audits.value = auditsRes.data.results || auditsRes.data
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
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.kpi-card {
    background: var(--p-surface-0);
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    position: relative;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.kpi-icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
}

.kpi-card.risk .kpi-icon {
    background: rgba(220, 38, 38, 0.1);
    color: #dc2626;
}

.kpi-card.compliance .kpi-icon {
    background: rgba(22, 163, 74, 0.1);
    color: #16a34a;
}

.kpi-card.tasks .kpi-icon {
    background: rgba(8, 145, 178, 0.1);
    color: #0891b2;
}

.kpi-card.findings .kpi-icon {
    background: rgba(234, 88, 12, 0.1);
    color: #ea580c;
}

.kpi-content {
    display: flex;
    flex-direction: column;
}

.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--p-text-color);
}

.kpi-label {
    font-size: 0.9rem;
    color: var(--p-text-muted-color);
}

.kpi-badge {
    position: absolute;
    top: 1rem;
    right: 1rem;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}

:dir(rtl) .kpi-badge {
    right: auto;
    left: 1rem;
}

.kpi-badge.critical {
    background: rgba(220, 38, 38, 0.1);
    color: #dc2626;
}

.kpi-badge.warning {
    background: rgba(234, 88, 12, 0.1);
    color: #ea580c;
}

.charts-row,
.tables-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.chart-card :deep(.p-card-content) {
    height: 300px;
}

.table-card :deep(.p-datatable) {
    font-size: 0.9rem;
}

/* Dark mode */
.dark-mode .kpi-card {
    background: var(--p-surface-800);
}
</style>
