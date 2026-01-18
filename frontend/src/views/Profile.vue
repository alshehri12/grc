<template>
    <div class="profile-page">
        <div class="page-header">
            <h1>{{ $t('nav.profile') }}</h1>
            <p>الملف الشخصي - User Profile</p>
        </div>
        
        <Card>
            <template #content>
                <div class="profile-content">
                    <Avatar 
                        :label="authStore.userFullName?.charAt(0) || 'U'" 
                        size="xlarge" 
                        shape="circle"
                        class="profile-avatar"
                    />
                    
                    <div class="profile-info">
                        <h2>{{ authStore.userFullName }}</h2>
                        <p class="email">{{ authStore.user?.email }}</p>
                        <p class="job-title">{{ authStore.user?.profile?.job_title }}</p>
                    </div>
                </div>
                
                <Divider />
                
                <form class="profile-form">
                    <div class="form-row">
                        <div class="form-field">
                            <label>First Name</label>
                            <InputText v-model="form.first_name" />
                        </div>
                        <div class="form-field">
                            <label>Last Name</label>
                            <InputText v-model="form.last_name" />
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-field">
                            <label>الاسم الأول (Arabic)</label>
                            <InputText v-model="form.first_name_ar" dir="rtl" />
                        </div>
                        <div class="form-field">
                            <label>اسم العائلة (Arabic)</label>
                            <InputText v-model="form.last_name_ar" dir="rtl" />
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-field">
                            <label>Phone</label>
                            <InputText v-model="form.phone" />
                        </div>
                        <div class="form-field">
                            <label>Mobile</label>
                            <InputText v-model="form.mobile" />
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-field">
                            <label>Job Title</label>
                            <InputText v-model="form.job_title" />
                        </div>
                        <div class="form-field">
                            <label>المسمى الوظيفي (Arabic)</label>
                            <InputText v-model="form.job_title_ar" dir="rtl" />
                        </div>
                    </div>
                    
                    <div class="form-actions">
                        <Button :label="$t('common.save')" @click="saveProfile" />
                    </div>
                </form>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import Avatar from 'primevue/avatar'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const toast = useToast()

const form = ref({
    first_name: '',
    last_name: '',
    first_name_ar: '',
    last_name_ar: '',
    phone: '',
    mobile: '',
    job_title: '',
    job_title_ar: ''
})

const loadProfile = () => {
    if (authStore.user) {
        form.value = {
            first_name: authStore.user.first_name || '',
            last_name: authStore.user.last_name || '',
            first_name_ar: authStore.user.profile?.first_name_ar || '',
            last_name_ar: authStore.user.profile?.last_name_ar || '',
            phone: authStore.user.profile?.phone || '',
            mobile: authStore.user.profile?.mobile || '',
            job_title: authStore.user.profile?.job_title || '',
            job_title_ar: authStore.user.profile?.job_title_ar || ''
        }
    }
}

const saveProfile = async () => {
    try {
        // API call to save profile
        toast.add({ severity: 'success', summary: 'Success', detail: 'Profile updated', life: 3000 })
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to update profile', life: 3000 })
    }
}

onMounted(() => {
    loadProfile()
})
</script>

<style scoped>
.profile-page {
    max-width: 800px;
}

.page-header {
    margin-bottom: 2rem;
}

.page-header h1 { margin: 0; }
.page-header p { margin: 0.25rem 0 0; color: var(--p-text-muted-color); }

.profile-content {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.profile-avatar {
    font-size: 2rem;
    background: var(--p-primary-color);
    color: white;
}

.profile-info h2 {
    margin: 0;
}

.profile-info .email {
    color: var(--p-text-muted-color);
    margin: 0.25rem 0;
}

.profile-info .job-title {
    color: var(--p-primary-color);
    margin: 0;
}

.profile-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.form-field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.form-field label {
    font-weight: 500;
    font-size: 0.9rem;
}

.form-field :deep(.p-inputtext) {
    width: 100%;
}

.form-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 1rem;
}
</style>
