import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import Ripple from 'primevue/ripple'

import App from './App.vue'
import router from './router'
import i18n from './i18n'

// PrimeVue Icons
import 'primeicons/primeicons.css'

// Custom styles
import './assets/main.css'

const app = createApp(App)

// Pinia store
app.use(createPinia())

// Vue Router
app.use(router)

// Vue i18n
app.use(i18n)

// PrimeVue with Aura theme (supports RTL)
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            prefix: 'p',
            darkModeSelector: '.dark-mode',
            cssLayer: false
        }
    },
    ripple: true,
    locale: {
        // Arabic locale will be loaded dynamically
    }
})

app.use(ToastService)
app.use(ConfirmationService)

// Directives
app.directive('tooltip', Tooltip)
app.directive('ripple', Ripple)

app.mount('#app')
