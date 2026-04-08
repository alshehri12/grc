<template>
    <div class="documents-page">
        <div class="page-header">
            <div>
                <h1>{{ $t('governance.documents') }}</h1>
                <p>{{ appStore.locale === 'ar' ? 'التحكم بالوثائق' : 'Document Control' }}</p>
            </div>
            <Button :label="$t('common.create')" icon="pi pi-plus" @click="openCreateDialog" />
        </div>

        <Card>
            <template #content>
                <DataTable :value="documents" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
                    <template #empty>
                        <div class="empty-message">
                            <i class="pi pi-file" style="font-size: 3rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                        </div>
                    </template>
                    <Column field="document_id" header="ID" sortable style="width: 100px"></Column>
                    <Column field="title" header="Title">
                        <template #body="{ data }">
                            <div>
                                <span>{{ data.title }}</span>
                                <div class="text-muted" v-if="data.title_ar">{{ data.title_ar }}</div>
                            </div>
                        </template>
                    </Column>
                    <Column field="document_type" header="Type"></Column>
                    <Column field="status" header="Status">
                        <template #body="{ data }">
                            <Tag :severity="getStatusSeverity(data.status)">{{ data.status }}</Tag>
                        </template>
                    </Column>
                    <Column field="classification" header="Classification"></Column>
                    <Column header="Actions" style="width: 150px">
                        <template #body="{ data }">
                            <Button icon="pi pi-pencil" text rounded @click="openEditDialog(data)" />
                            <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>

        <Dialog v-model:visible="dialogVisible" :header="isEdit ? 'Edit Document - تعديل الوثيقة' : 'New Document - وثيقة جديدة'" :style="{ width: '820px' }" modal>
            <div class="dialog-content">
                <div class="form-row">
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'معرف الوثيقة' : 'Document ID' }} <span class="required">*</span></label>
                        <InputText v-model="form.document_id" />
                    </div>
                    <div class="form-field">
                        <label>{{ appStore.locale === 'ar' ? 'النوع' : 'Type' }} <span class="required">*</span></label>
                        <Dropdown v-model="form.document_type" :options="documentTypeOptions" optionLabel="label" optionValue="value" />
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
                        <label>Description</label>
                        <Textarea v-model="form.description" rows="2" />
                    </div>
                    <div class="form-field">
                        <label>الوصف</label>
                        <Textarea v-model="form.description_ar" rows="2" dir="rtl" />
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label>Status</label>
                        <Dropdown v-model="form.status" :options="statusOptions" optionLabel="label" optionValue="value" />
                    </div>
                    <div class="form-field">
                        <label>Classification</label>
                        <Dropdown v-model="form.classification" :options="classificationOptions" optionLabel="label" optionValue="value" />
                    </div>
                </div>

                <div class="form-field">
                    <label>File <span class="required" v-if="!isEdit">*</span></label>
                    <input type="file" @change="onFileChange" />
                </div>
            </div>

            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="saveDocument" :loading="saving" />
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

const documents = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const selectedDocument = ref(null)
const selectedFile = ref(null)

const form = ref({
    document_id: '',
    title: '',
    title_ar: '',
    description: '',
    description_ar: '',
    document_type: 'other',
    status: 'draft',
    classification: 'internal'
})

const documentTypeOptions = [
    { label: 'Policy - سياسة', value: 'policy' },
    { label: 'Procedure - إجراء', value: 'procedure' },
    { label: 'Standard - معيار', value: 'standard' },
    { label: 'Guideline - دليل', value: 'guideline' },
    { label: 'Form - نموذج', value: 'form' },
    { label: 'Template - قالب', value: 'template' },
    { label: 'Record - سجل', value: 'record' },
    { label: 'Other - أخرى', value: 'other' }
]

const statusOptions = [
    { label: 'Draft - مسودة', value: 'draft' },
    { label: 'Active - نشط', value: 'active' },
    { label: 'Under Review - قيد المراجعة', value: 'under_review' },
    { label: 'Archived - مؤرشف', value: 'archived' }
]

const classificationOptions = [
    { label: 'Public - عام', value: 'public' },
    { label: 'Internal - داخلي', value: 'internal' },
    { label: 'Confidential - سري', value: 'confidential' },
    { label: 'Restricted - مقيد', value: 'restricted' }
]

const getStatusSeverity = (status) => {
    const map = {
        draft: 'secondary',
        active: 'success',
        under_review: 'warn',
        archived: 'secondary'
    }
    return map[status] || 'info'
}

const resetForm = () => {
    form.value = {
        document_id: '',
        title: '',
        title_ar: '',
        description: '',
        description_ar: '',
        document_type: 'other',
        status: 'draft',
        classification: 'internal'
    }
    selectedFile.value = null
}

const onFileChange = (event) => {
    selectedFile.value = event.target.files?.[0] || null
}

const loadDocuments = async () => {
    loading.value = true
    try {
        const orgId = appStore.currentOrganization?.id
        const response = await governanceApi.documents.list({ organization: orgId })
        documents.value = response.data.results || response.data
    } catch (error) {
        console.error('Failed to load documents:', error)
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
    selectedDocument.value = item
    const response = await governanceApi.documents.get(item.id)
    form.value = { ...form.value, ...response.data }
    selectedFile.value = null
    dialogVisible.value = true
}

const saveDocument = async () => {
    if (!form.value.document_id || !form.value.title || !form.value.document_type) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'Please fill required fields', life: 3000 })
        return
    }
    const orgId = await appStore.ensureOrganization()
    if (!orgId) {
        toast.add({ severity: 'warn', summary: 'Organization Required', detail: 'Please select an organization first', life: 3000 })
        return
    }
    if (!isEdit.value && !selectedFile.value) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: 'File is required for new document', life: 3000 })
        return
    }

    saving.value = true
    try {
        const data = new FormData()
        data.append('organization', orgId)
        data.append('document_id', form.value.document_id)
        data.append('title', form.value.title)
        data.append('title_ar', form.value.title_ar || '')
        data.append('description', form.value.description || '')
        data.append('description_ar', form.value.description_ar || '')
        data.append('document_type', form.value.document_type)
        data.append('status', form.value.status)
        data.append('classification', form.value.classification)
        if (selectedFile.value) {
            data.append('file', selectedFile.value)
        }

        if (isEdit.value && selectedDocument.value?.id) {
            await governanceApi.documents.update(selectedDocument.value.id, data)
        } else {
            await governanceApi.documents.create(data)
        }
        toast.add({ severity: 'success', summary: 'Success', detail: 'Document saved successfully', life: 3000 })
        dialogVisible.value = false
        await loadDocuments()
    } catch (error) {
        console.error('Failed to save document:', error)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save document', life: 3000 })
    } finally {
        saving.value = false
    }
}

const confirmDelete = (item) => {
    confirm.require({
        message: `Delete document "${item.title}"?`,
        header: 'Confirm Delete',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            await governanceApi.documents.delete(item.id)
            await loadDocuments()
            toast.add({ severity: 'success', summary: 'Deleted', detail: 'Document deleted', life: 3000 })
        }
    })
}

onMounted(() => {
    loadDocuments()
})
</script>

<style scoped>
.documents-page { display: flex; flex-direction: column; gap: 1.5rem; }
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
