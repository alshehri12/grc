<template>
    <div class="evidence-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('compliance.evidence') }}</h1>
                <p>{{ appStore.locale === 'ar' ? 'جمع الأدلة' : 'Evidence Collection' }}</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>

        <Card>
            <template #content>
                <DataTable :value="evidenceList" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-folder-open" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                        </div>
                    </template>
                    <Column field="evidence_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="evidence_type" header="Type"></Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column field="collection_date" header="Collected"></Column>
                    <Column field="valid_until" header="Valid Until"></Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-pencil" text rounded @click="openEditDialog(data)" />
                            <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>

        <Dialog v-model:visible="dialogVisible" :header="isEdit ? 'Edit Evidence - تعديل الدليل' : 'New Evidence - دليل جديد'" :style="{ width: '820px' }" modal>
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'معرف الدليل' : 'Evidence ID' }} <span class="required">*</span></label>
                        <InputText v-model="form.evidence_id" />
                    </div>
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'تطبيق الضابط' : 'Control Implementation' }} <span class="required">*</span></label>
                        <Dropdown
                            v-model="form.control_implementation"
                            :options="implementations"
                            optionLabel="control_title"
                            optionValue="id"
                            filter
                        />
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
                        <label>Evidence Type</label>
                        <Dropdown v-model="form.evidence_type" :options="typeOptions" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="form-field">
                        <label>Status</label>
                        <Dropdown v-model="form.status" :options="statusOptions" optionLabel="label" optionValue="value" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Collection Date <span class="required">*</span></label>
                        <Calendar v-model="form.collection_date" dateFormat="yy-mm-dd" showIcon />
                    </div>
                    <div class="form-field">
                        <label>Valid From <span class="required">*</span></label>
                        <Calendar v-model="form.valid_from" dateFormat="yy-mm-dd" showIcon />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Valid Until <span class="required">*</span></label>
                        <Calendar v-model="form.valid_until" dateFormat="yy-mm-dd" showIcon />
                    </div>
                    <div class="form-field">
                        <label>File <span class="required" v-if="!isEdit">*</span></label>
                        <input type="file" @change="onFileChange" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Description</label>
                        <Textarea v-model="form.description" rows="2" />
                    </div>
                    <div class="form-field">
                        <label>الوصف</label>
                        <Textarea v-model="form.description_ar" rows="2" dir="rtl" />
                    </div>
                </div>
            </div>

            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveEvidence" :loading="saving" />
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
import Calendar from 'primevue/calendar'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { complianceApi } from '@/api'

const appStore = useAppStore()
const confirm = useConfirm()
const toast = useToast()

const evidenceList = ref([])
const implementations = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const selectedEvidence = ref(null)
const selectedFile = ref(null)

const form = ref({
    evidence_id: '',
    control_implementation: null,
    title: '',
    title_ar: '',
    evidence_type: 'document',
    status: 'draft',
    description: '',
    description_ar: '',
    collection_date: null,
    valid_from: null,
    valid_until: null
})

const typeOptions = [
    { label: 'Document - مستند', value: 'document' },
    { label: 'Screenshot - لقطة شاشة', value: 'screenshot' },
    { label: 'System Log - سجل نظام', value: 'log' },
    { label: 'Report - تقرير', value: 'report' },
    { label: 'Configuration - إعدادات', value: 'configuration' },
    { label: 'Interview Notes - مقابلة', value: 'interview' },
    { label: 'Observation - ملاحظة', value: 'observation' },
    { label: 'Other - أخرى', value: 'other' }
]

const statusOptions = [
    { label: 'Draft - مسودة', value: 'draft' },
    { label: 'Submitted - مُرسل', value: 'submitted' },
    { label: 'Accepted - مقبول', value: 'accepted' },
    { label: 'Rejected - مرفوض', value: 'rejected' },
    { label: 'Expired - منتهي', value: 'expired' }
]

const getStatusSeverity = (status) => {
    const map = {
        draft: 'secondary',
        submitted: 'info',
        accepted: 'success',
        rejected: 'danger',
        expired: 'warn'
    }
    return map[status] || 'info'
}

const formatDate = (date) => {
    if (!date) return null
    if (typeof date === 'string') return date.split('T')[0]
    if (date instanceof Date) return date.toISOString().split('T')[0]
    return null
}

const resetForm = () => {
    form.value = {
        evidence_id: '',
        control_implementation: null,
        title: '',
        title_ar: '',
        evidence_type: 'document',
        status: 'draft',
        description: '',
        description_ar: '',
        collection_date: null,
        valid_from: null,
        valid_until: null
    }
    selectedFile.value = null
}

const onFileChange = (event) => {
    selectedFile.value = event.target.files?.[0] || null
}

const loadData = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const [evidenceRes, implRes] = await Promise.all([
            complianceApi.evidence.list({ organization: orgId }),
            complianceApi.implementations.list({ organization: orgId })
        ])
        evidenceList.value = evidenceRes.data.results || evidenceRes.data
        implementations.value = implRes.data.results || implRes.data
    } catch (error) {
        console.error('Failed to load evidence data:', error)
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
    selectedEvidence.value = item
    const response = await complianceApi.evidence.get(item.id)
    form.value = { ...form.value, ...response.data }
    selectedFile.value = null
    dialogVisible.value = true
}

const saveEvidence = async () => {
    if (!form.value.evidence_id || !form.value.control_implementation || !form.value.title || !form.value.collection_date || !form.value.valid_from || !form.value.valid_until) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill required fields', life: 3000 })
        return
    }
    const orgId = await appStore.ensureOrganization()
    if (!orgId) {
        toast.add({ severity: 'warn', summary: 'Organization Required', detail: 'Please select an organization first', life: 3000 })
        return
    }
    if (!isEdit.value && !selectedFile.value) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'File is required for new evidence', life: 3000 })
        return
    }

    saving.value = true
    try {
        const data = new FormData()
        data.append('organization', orgId)
        data.append('control_implementation', form.value.control_implementation)
        data.append('evidence_id', form.value.evidence_id)
        data.append('title', form.value.title)
        data.append('title_ar', form.value.title_ar || '')
        data.append('evidence_type', form.value.evidence_type)
        data.append('status', form.value.status)
        data.append('description', form.value.description || '')
        data.append('description_ar', form.value.description_ar || '')
        data.append('collection_date', formatDate(form.value.collection_date))
        data.append('valid_from', formatDate(form.value.valid_from))
        data.append('valid_until', formatDate(form.value.valid_until))
        if (selectedFile.value) {
            data.append('file', selectedFile.value)
        }

        if (isEdit.value && selectedEvidence.value?.id) {
            await complianceApi.evidence.update(selectedEvidence.value.id, data)
        } else {
            await complianceApi.evidence.create(data)
        }
        toast.add({ severity: 'success', summary: 'Success', detail: 'Evidence saved successfully', life: 3000 })
        dialogVisible.value = false
        await loadData()
    } catch (error) {
        console.error('Failed to save evidence:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save evidence', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (item) => {
    confirm.require({
        message: `Delete evidence "${item.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            await complianceApi.evidence.delete(item.id)
            await loadData()
            toast.add({ severity: 'success', summary: 'Deleted', detail: 'Evidence deleted', life: 3000 })
        }
    })
}

onMounted(() => {
    loadData()
})
</script>

<style scoped>
.evidence-page { display: flex; flex-direction: column; gap: 1.5rem; }
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
.form-field :deep(.p-calendar),
.form-field :deep(.p-inputtextarea) { width: 100%; }
</style>
