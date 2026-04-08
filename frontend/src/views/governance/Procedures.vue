<template>
    <div class="procedures-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('governance.procedures') }}</h1>
                <p>{{ appStore.locale === 'ar' ? 'إدارة الإجراءات' : 'Procedures Management' }}</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>

        <Card>
            <template #content>
                <DataTable :value="procedures" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-file-edit" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                        </div>
                    </template>
                    <Column field="procedure_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="policy_title" header="Policy"></Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column field="version" header="Version"></Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-pencil" text rounded @click="openEditDialog(data)" />
                            <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>

        <Dialog v-model:visible="dialogVisible" :header="isEdit ? 'Edit Procedure - تعديل الإجراء' : 'New Procedure - إجراء جديد'" :style="{ width: '840px' }" modal>
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'معرف الإجراء' : 'Procedure ID' }} <span class="required">*</span></label>
                        <InputText v-model="form.procedure_id" placeholder="PRC-001" />
                    </div>
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'السياسة' : 'Policy' }}</label>
                        <Dropdown v-model="form.policy" :options="policies" optionLabel="title" optionValue="id" showClear filter />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'العنوان' : 'Title' }} <span class="required">*</span></label>
                        <InputText v-model="form.title" />
                    </div>
                    <div class="form-field" v-if="appStore.locale === 'ar'">
                        <label>العنوان</label>
                        <InputText v-model="form.title_ar" dir="rtl" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Purpose <span class="required">*</span></label>
                        <Textarea v-model="form.purpose" rows="2" />
                    </div>
                    <div class="form-field">
                        <label>الغرض</label>
                        <Textarea v-model="form.purpose_ar" rows="2" dir="rtl" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Scope <span class="required">*</span></label>
                        <Textarea v-model="form.scope" rows="2" />
                    </div>
                    <div class="form-field">
                        <label>النطاق</label>
                        <Textarea v-model="form.scope_ar" rows="2" dir="rtl" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Procedure Steps <span class="required">*</span></label>
                        <Textarea v-model="form.procedure_steps" rows="4" />
                    </div>
                    <div class="form-field">
                        <label>خطوات الإجراء</label>
                        <Textarea v-model="form.procedure_steps_ar" rows="4" dir="rtl" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Status</label>
                        <Dropdown v-model="form.status" :options="statusOptions" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="form-field">
                        <label>Version</label>
                        <InputText v-model="form.version" />
                    </div>
                </div>
            </div>

            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveProcedure" :loading="saving" />
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { governanceApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const procedures = ref([])
const policies = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const selectedProcedure = ref(null)

const statusOptions = [
    { label: 'Draft - مسودة', value: 'draft' },
    { label: 'Pending Review - بانتظار المراجعة', value: 'pending_review' },
    { label: 'Pending Approval - بانتظار الاعتماد', value: 'pending_approval' },
    { label: 'Approved - معتمد', value: 'approved' },
    { label: 'Published - منشور', value: 'published' },
    { label: 'Retired - متقاعد', value: 'retired' }
]

const form = ref({
    procedure_id: '',
    title: '',
    title_ar: '',
    policy: null,
    purpose: '',
    purpose_ar: '',
    scope: '',
    scope_ar: '',
    procedure_steps: '',
    procedure_steps_ar: '',
    version: '1.0',
    status: 'draft'
})

const getStatusSeverity = (status) => {
    const map = {
        draft: 'secondary',
        pending_review: 'warn',
        pending_approval: 'warn',
        approved: 'info',
        published: 'success',
        retired: 'secondary'
    }
    return map[status] || 'info'
}

const resetForm = () => {
    form.value = {
        procedure_id: '',
        title: '',
        title_ar: '',
        policy: null,
        purpose: '',
        purpose_ar: '',
        scope: '',
        scope_ar: '',
        procedure_steps: '',
        procedure_steps_ar: '',
        version: '1.0',
        status: 'draft'
    }
}

const loadData = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const [procRes, polRes] = await Promise.all([
            governanceApi.procedures.list({ organization: orgId }),
            governanceApi.policies.list({ organization: orgId })
        ])
        procedures.value = procRes.data.results || procRes.data
        policies.value = polRes.data.results || polRes.data
    } catch (error) {
        console.error('Failed to load procedures data:', error)
    } finally {
        loading.value = false
    }
}

const openCreateDialog = () => {
    isEdit.value = false
    resetForm()
    dialogVisible.value = true
}

const openEditDialog = async (item) => {
    isEdit.value = true
    selectedProcedure.value = item
    const response = await governanceApi.procedures.get(item.id)
    form.value = { ...form.value, ...response.data }
    dialogVisible.value = true
}

const saveProcedure = async () => {
    if (!form.value.procedure_id || !form.value.title || !form.value.purpose || !form.value.scope || !form.value.procedure_steps) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill all required fields', life: 3000 })
        return
    }
    const orgId = await appStore.ensureOrganization()
    if (!orgId) {
        toast.add({ severity: 'warn', summary: 'Organization Required', detail: 'Please select an organization first', life: 3000 })
        return
    }

    saving.value = true
    try {
        const data = { ...form.value, organization: orgId }
        if (isEdit.value && selectedProcedure.value?.id) {
            await governanceApi.procedures.update(selectedProcedure.value.id, data)
        } else {
            await governanceApi.procedures.create(data)
        }
        toast.add({ severity: 'success', summary: 'Success', detail: 'Procedure saved successfully', life: 3000 })
        dialogVisible.value = false
        await loadData()
    } catch (error) {
        console.error('Failed to save procedure:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save procedure', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (item) => {
    confirm.require({
        message: `Delete procedure "${item.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            await governanceApi.procedures.delete(item.id)
            await loadData()
            toast.add({ severity: 'success', summary: 'Deleted', detail: 'Procedure deleted', life: 3000 })
        }
    })
}

onMounted(() => {
    loadData()
})
</script>

<style scoped>
.procedures-page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
.page-header h1 { margin: 0; }
.page-header p { margin: 0.25rem 0 0; color: var(--p-text-muted-color); }
.text-muted { font-size: 0.85rem; color: var(--p-text-muted-color); }
.empty-message { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 3rem; }
.dialog-content { display: flex; flex-direction: column; gap: 1rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-field { display: flex; flex-direction: column; gap: 0.5rem; }
.form-field label { font-weight: 500; font-size: 0.9rem; }
.form-field .required { color: var(--p-red-500); }
.form-field :deep(.p-inputtext),
.form-field :deep(.p-dropdown),
.form-field :deep(.p-inputtextarea) { width: 100%; }
</style>
