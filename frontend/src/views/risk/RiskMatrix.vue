<template>
    <div class="risk-matrix-page">
        <div class="page-header">
            <h1>{{ $t('risk.matrix') }}</h1>
            <p>مصفوفة المخاطر - Risk Heat Map</p>
        </div>
        
        <Card>
            <template #content>
                <div class="matrix-container">
                    <div class="matrix-y-label">
                        <span>Likelihood</span>
                        <span>الاحتمالية</span>
                    </div>
                    
                    <div class="matrix-grid">
                        <div 
                            v-for="(row, rowIdx) in matrix" 
                            :key="rowIdx"
                            class="matrix-row"
                        >
                            <div 
                                v-for="(cell, colIdx) in row" 
                                :key="colIdx"
                                class="matrix-cell"
                                :class="getCellClass(4 - rowIdx, colIdx)"
                            >
                                <div class="cell-risks">
                                    <span 
                                        v-for="risk in cell" 
                                        :key="risk.id"
                                        class="risk-dot"
                                        v-tooltip="risk.title"
                                    >
                                        {{ risk.risk_id }}
                                    </span>
                                </div>
                                <div class="cell-count" v-if="cell.length > 0">
                                    {{ cell.length }}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="matrix-x-label">
                        <span>Impact</span>
                        <span>الأثر</span>
                    </div>
                </div>
                
                <div class="matrix-legend">
                    <span class="legend-item critical">Critical (حرج)</span>
                    <span class="legend-item high">High (عالي)</span>
                    <span class="legend-item medium">Medium (متوسط)</span>
                    <span class="legend-item low">Low (منخفض)</span>
                </div>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import { useAppStore } from '@/stores/app'
import { riskApi } from '@/api'

const appStore = useAppStore()
const matrix = ref([[],[],[],[],[]])

const getCellClass = (likelihood, impact) => {
    const score = (likelihood + 1) * (impact + 1)
    if (score >= 20) return 'critical'
    if (score >= 12) return 'high'
    if (score >= 6) return 'medium'
    return 'low'
}

const loadMatrix = async () => {
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await riskApi.risks.matrix(orgId)
        matrix.value = response.data.matrix
    } catch (error) {
        console.error('Failed to load risk matrix:', error)
    }
}

onMounted(() => {
    loadMatrix()
})
</script>

<style scoped>
.risk-matrix-page {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.page-header h1 { margin: 0; }
.page-header p { margin: 0.25rem 0 0; color: var(--p-text-muted-color); }

.matrix-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem;
}

.matrix-y-label {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    transform: rotate(180deg);
    position: absolute;
    left: 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-weight: 600;
}

.matrix-grid {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.matrix-row {
    display: flex;
    gap: 4px;
}

.matrix-cell {
    width: 100px;
    height: 80px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
}

.matrix-cell.critical { background: rgba(220, 38, 38, 0.8); }
.matrix-cell.high { background: rgba(234, 88, 12, 0.7); }
.matrix-cell.medium { background: rgba(202, 138, 4, 0.6); }
.matrix-cell.low { background: rgba(22, 163, 74, 0.5); }

.cell-risks {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    max-width: 90px;
    justify-content: center;
}

.risk-dot {
    font-size: 0.7rem;
    background: white;
    padding: 2px 4px;
    border-radius: 4px;
    cursor: pointer;
}

.cell-count {
    position: absolute;
    bottom: 4px;
    right: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
}

.matrix-x-label {
    margin-top: 1rem;
    display: flex;
    gap: 1rem;
    font-weight: 600;
}

.matrix-legend {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    margin-top: 2rem;
}

.legend-item {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-size: 0.85rem;
}

.legend-item.critical { background: rgba(220, 38, 38, 0.2); color: #dc2626; }
.legend-item.high { background: rgba(234, 88, 12, 0.2); color: #ea580c; }
.legend-item.medium { background: rgba(202, 138, 4, 0.2); color: #ca8a04; }
.legend-item.low { background: rgba(22, 163, 74, 0.2); color: #16a34a; }
</style>
