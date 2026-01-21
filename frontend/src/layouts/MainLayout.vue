<template>
    <div class="layout-wrapper" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
        <!-- Sidebar -->
        <aside class="layout-sidebar">
            <div class="sidebar-header">
                <img src="/logo.svg" alt="Logo" class="logo" v-if="!appStore.sidebarCollapsed" />
                <span class="app-name" v-if="!appStore.sidebarCollapsed">{{ $t('app.name') }}</span>
            </div>
            
            <nav class="sidebar-menu">
                <ul>
                    <li>
                        <router-link to="/" class="menu-item">
                            <i class="pi pi-home"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('nav.dashboard') }}</span>
                        </router-link>
                    </li>
                    
                    <!-- Governance -->
                    <li class="menu-section" v-if="!appStore.sidebarCollapsed">
                        {{ $t('governance.title') }}
                    </li>
                    <li>
                        <router-link to="/governance/policies" class="menu-item">
                            <i class="pi pi-file"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('governance.policies') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/governance/procedures" class="menu-item">
                            <i class="pi pi-list"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('governance.procedures') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/governance/documents" class="menu-item">
                            <i class="pi pi-folder"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('governance.documents') }}</span>
                        </router-link>
                    </li>
                    
                    <!-- Risk -->
                    <li class="menu-section" v-if="!appStore.sidebarCollapsed">
                        {{ $t('risk.title') }}
                    </li>
                    <li>
                        <router-link to="/risk/register" class="menu-item">
                            <i class="pi pi-exclamation-triangle"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('risk.register') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/risk/matrix" class="menu-item">
                            <i class="pi pi-th-large"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('risk.matrix') }}</span>
                        </router-link>
                    </li>
                    
                    <!-- BCM -->
                    <li class="menu-section" v-if="!appStore.sidebarCollapsed">
                        {{ $t('bcm.title') }}
                    </li>
                    <li>
                        <router-link to="/bcm/functions" class="menu-item">
                            <i class="pi pi-sitemap"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('bcm.functions') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/bcm/bia" class="menu-item">
                            <i class="pi pi-chart-bar"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('bcm.bia') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/bcm/plans" class="menu-item">
                            <i class="pi pi-shield"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('bcm.bcp') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/bcm/dr-plans" class="menu-item">
                            <i class="pi pi-server"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('bcm.drp') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/bcm/tests" class="menu-item">
                            <i class="pi pi-check-circle"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('bcm.tests') }}</span>
                        </router-link>
                    </li>
                    
                    <!-- Compliance -->
                    <li class="menu-section" v-if="!appStore.sidebarCollapsed">
                        {{ $t('compliance.title') }}
                    </li>
                    <li>
                        <router-link to="/compliance/controls" class="menu-item">
                            <i class="pi pi-check-square"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('compliance.controls') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/compliance/audits" class="menu-item">
                            <i class="pi pi-search"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('compliance.audits') }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/compliance/evidence" class="menu-item">
                            <i class="pi pi-paperclip"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('compliance.evidence') }}</span>
                        </router-link>
                    </li>
                    
                    <!-- Workflow -->
                    <li class="menu-section" v-if="!appStore.sidebarCollapsed">
                        {{ $t('workflow.title') || 'Workflow' }}
                    </li>
                    <li>
                        <router-link to="/workflow" class="menu-item">
                            <i class="pi pi-chart-line"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('workflow.dashboard') || 'Dashboard' }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/workflow/tasks" class="menu-item">
                            <i class="pi pi-inbox"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('workflow.tasks') || 'Task Inbox' }}</span>
                        </router-link>
                    </li>
                    <li>
                        <router-link to="/workflow/approvals" class="menu-item">
                            <i class="pi pi-check-square"></i>
                            <span v-if="!appStore.sidebarCollapsed">{{ $t('workflow.approvals') || 'Approvals' }}</span>
                        </router-link>
                    </li>
                </ul>
            </nav>
        </aside>
        
        <!-- Main Content -->
        <div class="layout-main">
            <!-- Top Bar -->
            <header class="layout-topbar">
                <div class="topbar-start">
                    <Button 
                        icon="pi pi-bars" 
                        text 
                        @click="appStore.toggleSidebar"
                        class="sidebar-toggle"
                    />
                </div>
                
                <div class="topbar-end">
                    <!-- Language Switcher -->
                    <Button 
                        :label="appStore.locale === 'ar' ? 'EN' : 'عربي'"
                        text
                        @click="toggleLanguage"
                        class="lang-switch"
                    />
                    
                    <!-- Theme Switcher -->
                    <Button 
                        :icon="appStore.darkMode ? 'pi pi-sun' : 'pi pi-moon'"
                        text
                        @click="appStore.toggleDarkMode"
                        v-tooltip="$t('settings.theme')"
                    />
                    
                    <!-- Notifications -->
                    <Button 
                        icon="pi pi-bell"
                        text
                        badge="3"
                        badgeSeverity="danger"
                        v-tooltip="'Notifications'"
                    />
                    
                    <!-- User Menu -->
                    <div class="user-menu">
                        <Avatar 
                            :label="authStore.userFullName?.charAt(0) || 'U'" 
                            shape="circle"
                            @click="toggleUserMenu"
                        />
                        <Menu ref="userMenuRef" :model="userMenuItems" popup />
                    </div>
                </div>
            </header>
            
            <!-- Page Content -->
            <main class="layout-content">
                <router-view />
            </main>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Menu from 'primevue/menu'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const { t, locale } = useI18n()
const appStore = useAppStore()
const authStore = useAuthStore()

const userMenuRef = ref(null)

const userMenuItems = computed(() => [
    {
        label: t('nav.profile'),
        icon: 'pi pi-user',
        command: () => router.push('/profile')
    },
    {
        label: t('nav.settings'),
        icon: 'pi pi-cog',
        command: () => router.push('/settings')
    },
    { separator: true },
    {
        label: t('nav.logout'),
        icon: 'pi pi-sign-out',
        command: async () => {
            await authStore.logout()
            router.push('/auth/login')
        }
    }
])

const toggleUserMenu = (event) => {
    userMenuRef.value.toggle(event)
}

const toggleLanguage = () => {
    const newLocale = appStore.locale === 'ar' ? 'en' : 'ar'
    appStore.setLocale(newLocale)
    locale.value = newLocale
}
</script>

<style scoped>
.layout-wrapper {
    display: flex;
    min-height: 100vh;
}

.layout-sidebar {
    width: 260px;
    background: var(--p-surface-0);
    border-right: 1px solid var(--p-surface-200);
    display: flex;
    flex-direction: column;
    transition: width 0.3s ease;
    position: fixed;
    height: 100vh;
    z-index: 100;
}

.sidebar-collapsed .layout-sidebar {
    width: 70px;
}

.sidebar-header {
    padding: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border-bottom: 1px solid var(--p-surface-200);
}

.logo {
    width: 40px;
    height: 40px;
}

.app-name {
    font-weight: 600;
    font-size: 1.1rem;
    color: var(--p-primary-color);
}

.sidebar-menu {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 0;
}

.sidebar-menu ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.menu-section {
    padding: 1rem 1.5rem 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--p-text-muted-color);
    letter-spacing: 0.05em;
}

.menu-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    color: var(--p-text-color);
    text-decoration: none;
    transition: all 0.2s ease;
}

.menu-item:hover {
    background: var(--p-surface-100);
}

.menu-item.router-link-active {
    background: var(--p-primary-50);
    color: var(--p-primary-color);
    border-right: 3px solid var(--p-primary-color);
}

:dir(rtl) .menu-item.router-link-active {
    border-right: none;
    border-left: 3px solid var(--p-primary-color);
}

.menu-item i {
    font-size: 1.1rem;
    width: 24px;
    text-align: center;
}

.layout-main {
    flex: 1;
    margin-left: 260px;
    display: flex;
    flex-direction: column;
    transition: margin-left 0.3s ease;
}

:dir(rtl) .layout-main {
    margin-left: 0;
    margin-right: 260px;
}

.sidebar-collapsed .layout-main {
    margin-left: 70px;
}

:dir(rtl) .sidebar-collapsed .layout-main {
    margin-left: 0;
    margin-right: 70px;
}

.layout-topbar {
    height: 60px;
    padding: 0 1.5rem;
    background: var(--p-surface-0);
    border-bottom: 1px solid var(--p-surface-200);
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 50;
}

.topbar-start {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.topbar-end {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.lang-switch {
    font-weight: 600;
}

.user-menu {
    cursor: pointer;
}

.layout-content {
    flex: 1;
    padding: 1.5rem;
    background: var(--p-surface-50);
}

/* Dark mode adjustments */
.dark-mode .layout-sidebar,
.dark-mode .layout-topbar {
    background: var(--p-surface-900);
    border-color: var(--p-surface-700);
}

.dark-mode .layout-content {
    background: var(--p-surface-950);
}

.dark-mode .menu-item:hover {
    background: var(--p-surface-800);
}

.dark-mode .menu-item.router-link-active {
    background: rgba(var(--p-primary-500), 0.1);
}
</style>
