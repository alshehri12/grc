<template>
    <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-field">
            <label for="username">{{ $t('auth.username') }}</label>
            <InputText 
                id="username"
                v-model="username"
                :placeholder="$t('auth.username')"
                :class="{ 'p-invalid': error }"
                autocomplete="username"
            />
        </div>
        
        <div class="form-field">
            <label for="password">{{ $t('auth.password') }}</label>
            <Password 
                id="password"
                v-model="password"
                :placeholder="$t('auth.password')"
                :feedback="false"
                :toggleMask="true"
                :class="{ 'p-invalid': error }"
                autocomplete="current-password"
            />
        </div>
        
        <div class="form-options">
            <div class="remember-me">
                <Checkbox id="remember" v-model="rememberMe" :binary="true" />
                <label for="remember">{{ $t('auth.rememberMe') }}</label>
            </div>
            <a href="#" class="forgot-link">{{ $t('auth.forgotPassword') }}</a>
        </div>
        
        <Message v-if="error" severity="error" :closable="false">
            {{ error }}
        </Message>
        
        <Button 
            type="submit"
            :label="$t('auth.login')"
            :loading="loading"
            class="login-button"
        />
    </form>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const rememberMe = ref(false)
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
    error.value = ''
    loading.value = true
    
    try {
        const success = await authStore.login(username.value, password.value)
        
        if (success) {
            router.push('/')
        } else {
            error.value = authStore.error
        }
    } catch (err) {
        error.value = 'An error occurred. Please try again.'
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.login-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

.form-field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.form-field label {
    font-weight: 500;
    color: var(--p-text-color);
}

.form-field :deep(.p-inputtext),
.form-field :deep(.p-password-input) {
    width: 100%;
    padding: 0.75rem 1rem;
}

.form-options {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.remember-me {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.remember-me label {
    font-size: 0.9rem;
    color: var(--p-text-muted-color);
    cursor: pointer;
}

.forgot-link {
    font-size: 0.9rem;
    color: var(--p-primary-color);
    text-decoration: none;
}

.forgot-link:hover {
    text-decoration: underline;
}

.login-button {
    width: 100%;
    padding: 0.75rem;
    font-weight: 600;
    margin-top: 0.5rem;
}
</style>
