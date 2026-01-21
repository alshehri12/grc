<template>
    <div class="auth-layout" :class="{ 'dark-mode': appStore.darkMode }">
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-header">
                    <a href="https://ncec.gov.sa/" target="_blank" class="logo-link">
                        <img src="/ncec-logo.jpg" alt="NCEC Logo" class="auth-logo" />
                    </a>
                </div>
                
                <router-view />
                
                <div class="auth-footer">
                    <Button 
                        :label="appStore.locale === 'ar' ? 'English' : 'العربية'"
                        text
                        size="small"
                        @click="toggleLanguage"
                    />
                    <span class="separator">|</span>
                    <Button 
                        :icon="appStore.darkMode ? 'pi pi-sun' : 'pi pi-moon'"
                        text
                        size="small"
                        @click="appStore.toggleDarkMode"
                    />
                </div>
            </div>
        </div>
        
        <div class="auth-background">
            <div class="bg-gradient"></div>
            <div class="bg-pattern"></div>
        </div>
    </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { useAppStore } from '@/stores/app'

const { locale } = useI18n()
const appStore = useAppStore()

const toggleLanguage = () => {
    const newLocale = appStore.locale === 'ar' ? 'en' : 'ar'
    appStore.setLocale(newLocale)
    locale.value = newLocale
}
</script>

<style scoped>
.auth-layout {
    min-height: 100vh;
    display: flex;
    position: relative;
    overflow: hidden;
}

.auth-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    position: relative;
    z-index: 10;
}

.auth-card {
    width: 100%;
    max-width: 420px;
    background: var(--p-surface-0);
    border-radius: 16px;
    padding: 2.5rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.auth-header {
    text-align: center;
    margin-bottom: 2rem;
}

.logo-link {
    display: inline-block;
}

.auth-logo {
    max-width: 320px;
    width: 100%;
    height: auto;
}

.auth-footer {
    margin-top: 2rem;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}

.separator {
    color: var(--p-text-muted-color);
}

.auth-background {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1;
}

.bg-gradient {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, #006837 0%, #0b4d26 50%, #004d2a 100%);
}

.bg-pattern {
    position: absolute;
    inset: 0;
    opacity: 0.1;
    background-image: 
        radial-gradient(circle at 25% 25%, white 2px, transparent 2px),
        radial-gradient(circle at 75% 75%, white 2px, transparent 2px);
    background-size: 50px 50px;
}

/* Dark mode */
.dark-mode .auth-card {
    background: var(--p-surface-900);
}

.dark-mode .bg-gradient {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
}

/* RTL Support */
:dir(rtl) .auth-card {
    direction: rtl;
}
</style>
