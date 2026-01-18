<template>
    <div class="page">
        <div class="page-header">
            <h1>{{ $t('governance.procedures') }}</h1>
            <p>الإجراءات - Procedures Management</p>
        </div>
        <Card>
            <template #content>
                <p class="placeholder-text">Procedures list will be displayed here</p>
            </template>
        </Card>
    </div>
</template>

<script setup>
import Card from 'primevue/card'
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header h1 { margin: 0; }
.page-header p { margin: 0.25rem 0 0; color: var(--p-text-muted-color); }
.placeholder-text { color: var(--p-text-muted-color); text-align: center; padding: 3rem; }
</style>
