<template>
    <Toast />
    <ConfirmDialog />
    <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const { locale } = useI18n()
const appStore = useAppStore()
const authStore = useAuthStore()

onMounted(async () => {
    // Initialize app settings
    appStore.initialize()
    locale.value = appStore.locale
    
    // Initialize auth
    await authStore.initialize()
})
</script>

<style>
/* Cairo font for Arabic */
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-family-ar: 'Cairo', 'Inter', sans-serif;
    
    /* GRC Brand Colors */
    --grc-primary: #1e40af;
    --grc-secondary: #0891b2;
    --grc-success: #059669;
    --grc-warning: #d97706;
    --grc-danger: #dc2626;
    --grc-info: #0284c7;
}

html {
    font-size: 14px;
}

body {
    font-family: var(--font-family);
    margin: 0;
    padding: 0;
    min-height: 100vh;
}

/* RTL Support */
html[dir="rtl"] body,
html.rtl body {
    font-family: var(--font-family-ar);
}

/* Dark mode base */
.dark-mode {
    color-scheme: dark;
}
</style>
