<template>
    <div class="settings-page">
        <div class="page-header">
            <h1>{{ $t('settings.title') }}</h1>
            <p>الإعدادات - System Settings</p>
        </div>
        
        <div class="settings-grid">
            <Card>
                <template #title>{{ $t('settings.language') }}</template>
                <template #content>
                    <div class="setting-row">
                        <SelectButton 
                            v-model="selectedLocale" 
                            :options="localeOptions" 
                            optionLabel="label"
                            optionValue="value"
                            @change="handleLocaleChange"
                        />
                    </div>
                </template>
            </Card>
            
            <Card>
                <template #title>{{ $t('settings.theme') }}</template>
                <template #content>
                    <div class="setting-row">
                        <SelectButton 
                            v-model="selectedTheme" 
                            :options="themeOptions" 
                            optionLabel="label"
                            optionValue="value"
                            @change="handleThemeChange"
                        />
                    </div>
                </template>
            </Card>
            
            <Card>
                <template #title>{{ $t('settings.notifications') }}</template>
                <template #content>
                    <div class="setting-row">
                        <div class="setting-item">
                            <label>Email Notifications</label>
                            <ToggleButton v-model="emailNotifications" onLabel="On" offLabel="Off" />
                        </div>
                    </div>
                </template>
            </Card>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import SelectButton from 'primevue/selectbutton'
import ToggleButton from 'primevue/togglebutton'
import { useAppStore } from '@/stores/app'

const { locale } = useI18n()
const appStore = useAppStore()

const selectedLocale = ref(appStore.locale)
const selectedTheme = ref(appStore.darkMode ? 'dark' : 'light')
const emailNotifications = ref(true)

const localeOptions = [
    { label: 'English', value: 'en' },
    { label: 'العربية', value: 'ar' }
]

const themeOptions = [
    { label: '☀️ Light', value: 'light' },
    { label: '🌙 Dark', value: 'dark' }
]

const handleLocaleChange = () => {
    appStore.setLocale(selectedLocale.value)
    locale.value = selectedLocale.value
}

const handleThemeChange = () => {
    appStore.setDarkMode(selectedTheme.value === 'dark')
}
</script>

<style scoped>
.settings-page {
    max-width: 800px;
}

.page-header {
    margin-bottom: 2rem;
}

.page-header h1 { margin: 0; }
.page-header p { margin: 0.25rem 0 0; color: var(--p-text-muted-color); }

.settings-grid {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.setting-row {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.setting-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
</style>
