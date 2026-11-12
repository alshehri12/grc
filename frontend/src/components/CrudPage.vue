<template>
    <div class="crud-page">
        <div class="page-header">
            <div>
                <h1>{{ title }}</h1>
                <p v-if="subtitle">{{ subtitle }}</p>
            </div>
            <div class="header-actions">
                <slot name="header-actions" />
                <Button v-if="canCreate" :label="$t('common.create')" icon="pi pi-plus" @click="openCreate" />
            </div>
        </div>

        <slot name="above-table" :rows="rows" />

        <Card>
            <template #content>
                <div class="table-toolbar" v-if="searchable || $slots.filters">
                    <span class="p-input-icon-left" v-if="searchable">
                        <InputText v-model="search" :placeholder="$t('common.search')" @input="debouncedLoad" />
                    </span>
                    <slot name="filters" :reload="load" />
                </div>
                <DataTable :value="rows" :loading="loading" paginator :rows="pageSize" responsiveLayout="scroll"
                           :rowClass="rowClass" dataKey="id" sortMode="single">
                    <template #empty>
                        <div class="empty-message">
                            <i :class="emptyIcon" style="font-size: 2.5rem; color: var(--p-text-muted-color);"></i>
                            <p>{{ $t('common.noData') }}</p>
                        </div>
                    </template>
                    <Column v-for="col in columns" :key="col.field" :field="col.field" :header="col.header"
                            :sortable="col.sortable !== false" :style="col.style">
                        <template #body="{ data }">
                            <slot :name="`col-${col.field}`" :data="data" :value="get(data, col.field)">
                                <template v-if="col.type === 'tag'">
                                    <Tag v-if="get(data, col.field)" :severity="severity(col, get(data, col.field))">
                                        {{ label(col, get(data, col.field)) }}
                                    </Tag>
                                </template>
                                <template v-else-if="col.type === 'date'">{{ fmtDate(get(data, col.field)) }}</template>
                                <template v-else-if="col.type === 'bool'">
                                    <i :class="get(data, col.field) ? 'pi pi-check text-success' : 'pi pi-times text-muted'"></i>
                                </template>
                                <template v-else-if="col.type === 'progress'">
                                    <ProgressBar :value="Number(get(data, col.field) || 0)" :showValue="true" style="height: 1.1rem" />
                                </template>
                                <template v-else-if="col.type === 'money'">{{ fmtMoney(get(data, col.field)) }}</template>
                                <template v-else>
                                    <div>
                                        <span>{{ label(col, get(data, col.field)) }}</span>
                                        <div class="text-muted" v-if="col.subField && get(data, col.subField)">{{ get(data, col.subField) }}</div>
                                    </div>
                                </template>
                            </slot>
                        </template>
                    </Column>
                    <Column :header="$t('common.actions')" :style="{ width: actionsWidth }">
                        <template #body="{ data }">
                            <slot name="row-actions" :data="data" :reload="load" />
                            <Button v-if="$slots.view" icon="pi pi-eye" text rounded @click="openView(data)" v-tooltip="$t('common.view')" />
                            <Button v-if="canEdit(data)" icon="pi pi-pencil" text rounded @click="openEdit(data)" v-tooltip="$t('common.edit')" />
                            <Button v-if="canDelete(data)" icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" v-tooltip="$t('common.delete')" />
                        </template>
                    </Column>
                </DataTable>
            </template>
        </Card>

        <!-- Create / Edit -->
        <Dialog v-model:visible="dialogVisible" :header="isEdit ? editTitle : createTitle" :style="{ width: dialogWidth }" modal>
            <div class="dialog-content">
                <slot name="form-top" :form="form" :isEdit="isEdit" />
                <div class="form-grid">
                    <div v-for="f in visibleFields" :key="f.name" class="form-field" :class="{ full: f.full || ['textarea', 'multiselect'].includes(f.type) }">
                        <label>{{ f.label }} <span v-if="f.required" class="required">*</span></label>
                        <InputText v-if="!f.type || f.type === 'text'" v-model="form[f.name]" :placeholder="f.placeholder" :dir="f.dir" />
                        <Textarea v-else-if="f.type === 'textarea'" v-model="form[f.name]" :rows="f.rows || 3" :dir="f.dir" autoResize />
                        <InputNumber v-else-if="f.type === 'number'" v-model="form[f.name]" :min="f.min" :max="f.max"
                                     :minFractionDigits="f.decimals || 0" :maxFractionDigits="f.decimals || 0" :suffix="f.suffix" />
                        <Dropdown v-else-if="f.type === 'select'" v-model="form[f.name]" :options="optionsFor(f)" optionLabel="label" optionValue="value"
                                  :placeholder="f.placeholder || '-'" :showClear="!f.required" filter />
                        <MultiSelect v-else-if="f.type === 'multiselect'" v-model="form[f.name]" :options="optionsFor(f)" optionLabel="label" optionValue="value"
                                     :placeholder="f.placeholder || '-'" display="chip" filter />
                        <Calendar v-else-if="f.type === 'date'" v-model="form[f.name]" dateFormat="yy-mm-dd" showIcon />
                        <div v-else-if="f.type === 'switch'" class="switch-row"><InputSwitch v-model="form[f.name]" /></div>
                        <small v-if="f.help" class="text-muted">{{ f.help }}</small>
                    </div>
                </div>
                <slot name="form-bottom" :form="form" :isEdit="isEdit" />
            </div>
            <template #footer>
                <Button :label="$t('common.cancel')" text @click="dialogVisible = false" />
                <Button :label="$t('common.save')" icon="pi pi-check" @click="save" :loading="saving" />
            </template>
        </Dialog>

        <!-- View -->
        <Dialog v-model:visible="viewVisible" :header="viewTitle(selected)" :style="{ width: dialogWidth }" modal>
            <slot name="view" :data="selected" :reload="load" :close="() => viewVisible = false" />
        </Dialog>
    </div>
</template>

<script setup>
/**
 * Generic list + create/edit/view page driven by a column and field config.
 * Props:
 *  api        {list, create, update, delete}
 *  columns    [{field, header, type: text|tag|date|bool|progress|money, options, severities, subField, style}]
 *  fields     [{name, label, type: text|textarea|number|select|multiselect|date|switch, options|optionsKey, required, full, dir, min, max, decimals, help, showIf(form)}]
 *  lookups    {optionsKey: [{label, value}]}   (async options resolved by the parent)
 *  orgScoped  add organization id to list params and payload
 */
import { ref, computed, onMounted, watch } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import InputSwitch from 'primevue/inputswitch'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import MultiSelect from 'primevue/multiselect'
import Calendar from 'primevue/calendar'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
    title: String,
    subtitle: String,
    api: { type: Object, required: true },
    columns: { type: Array, required: true },
    fields: { type: Array, default: () => [] },
    lookups: { type: Object, default: () => ({}) },
    defaults: { type: Object, default: () => ({}) },
    listParams: { type: Object, default: () => ({}) },
    orgScoped: { type: Boolean, default: true },
    searchable: { type: Boolean, default: true },
    canCreate: { type: Boolean, default: true },
    editable: { type: [Boolean, Function], default: true },
    deletable: { type: [Boolean, Function], default: true },
    pageSize: { type: Number, default: 10 },
    dialogWidth: { type: String, default: '780px' },
    actionsWidth: { type: String, default: '170px' },
    emptyIcon: { type: String, default: 'pi pi-inbox' },
    itemLabel: { type: String, default: 'item' },
    titleField: { type: String, default: 'title' },
    rowClass: Function,
    transformOut: Function,   // (payload) => payload
    transformIn: Function,    // (row) => form
})
const emit = defineEmits(['loaded', 'saved'])

const appStore = useAppStore()
const authStore = useAuthStore()
const confirm = useConfirm()
const toast = useToast()

const rows = ref([])
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const dialogVisible = ref(false)
const viewVisible = ref(false)
const isEdit = ref(false)
const selected = ref(null)
const form = ref({})

const createTitle = computed(() => `New ${props.itemLabel}`)
const editTitle = computed(() => `Edit ${props.itemLabel}`)
const visibleFields = computed(() => props.fields.filter(f => !f.showIf || f.showIf(form.value)))
const viewTitle = (row) => row ? (row[props.titleField] || row.name || row.id) : ''

const get = (obj, path) => path.split('.').reduce((o, k) => (o == null ? o : o[k]), obj)
const optionsFor = (f) => f.options || props.lookups[f.optionsKey] || []
const label = (col, v) => {
    if (v == null) return '-'
    const opt = (col.options || props.lookups[col.optionsKey] || []).find(o => o.value === v)
    return opt ? opt.label : v
}
const severity = (col, v) => (col.severities && col.severities[v]) || 'info'
const fmtDate = (v) => v ? String(v).split('T')[0] : '-'
const fmtMoney = (v) => v == null ? '-' : Number(v).toLocaleString()
const canEdit = (row) => typeof props.editable === 'function' ? props.editable(row) : props.editable
const canDelete = (row) => typeof props.deletable === 'function' ? props.deletable(row) : props.deletable

let timer = null
const debouncedLoad = () => { clearTimeout(timer); timer = setTimeout(load, 350) }

const load = async () => {
    loading.value = true
    try {
        const params = { ...props.listParams, page_size: 200 }
        if (props.orgScoped) params.organization = await appStore.ensureOrganization()
        if (search.value) params.search = search.value
        const res = await props.api.list(params)
        rows.value = res.data.results || res.data
        emit('loaded', rows.value)
    } catch (e) {
        console.error('Failed to load', e)
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load data', life: 3000 })
    } finally {
        loading.value = false
    }
}

const blankForm = () => {
    const f = {}
    props.fields.forEach(x => { f[x.name] = x.type === 'multiselect' ? [] : (x.type === 'switch' ? false : null) })
    return { ...f, ...props.defaults }
}
const openCreate = () => { isEdit.value = false; selected.value = null; form.value = blankForm(); dialogVisible.value = true }
const openEdit = (row) => {
    isEdit.value = true; selected.value = row
    form.value = props.transformIn ? props.transformIn({ ...row }) : { ...row }
    dialogVisible.value = true
}
const openView = (row) => { selected.value = row; viewVisible.value = true }

const fmtOut = (v) => {
    if (v instanceof Date) return v.toISOString().split('T')[0]
    return v
}

const save = async () => {
    const missing = visibleFields.value.filter(f => f.required && (form.value[f.name] === null || form.value[f.name] === '' || form.value[f.name] === undefined))
    if (missing.length) {
        toast.add({ severity: 'warn', summary: 'Validation', detail: `Please fill: ${missing.map(m => m.label).join(', ')}`, life: 4000 })
        return
    }
    saving.value = true
    try {
        let payload = {}
        Object.entries(form.value).forEach(([k, v]) => { payload[k] = fmtOut(v) })
        if (props.orgScoped) payload.organization = await appStore.ensureOrganization()
        if (props.transformOut) payload = props.transformOut(payload)
        if (isEdit.value && selected.value?.id) {
            await props.api.update(selected.value.id, payload)
        } else {
            await props.api.create(payload)
        }
        toast.add({ severity: 'success', summary: 'Saved', detail: `${props.itemLabel} saved`, life: 2500 })
        dialogVisible.value = false
        emit('saved')
        await load()
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Error', detail: errorMessage(e), life: 6000 })
    } finally {
        saving.value = false
    }
}

const errorMessage = (e) => {
    const d = e.response?.data
    if (!d) return 'Request failed'
    if (typeof d === 'string') return d.slice(0, 200)
    if (d.error) return d.error
    if (d.detail) return d.detail
    const k = Object.keys(d)[0]
    return k ? `${k}: ${Array.isArray(d[k]) ? d[k].join(', ') : d[k]}` : 'Request failed'
}

const confirmDelete = (row) => {
    confirm.require({
        message: `Delete "${row[props.titleField] || row.name || row.id}"?`,
        header: 'Confirm Delete', icon: 'pi pi-exclamation-triangle', acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                await props.api.delete(row.id)
                toast.add({ severity: 'success', summary: 'Deleted', life: 2500 })
                await load()
            } catch (e) {
                toast.add({ severity: 'error', summary: 'Error', detail: errorMessage(e), life: 5000 })
            }
        }
    })
}

watch(() => props.listParams, debouncedLoad, { deep: true })
onMounted(load)
defineExpose({ load, openEdit, openView, errorMessage })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; gap: 1rem; flex-wrap: wrap; }
.page-header h1 { margin: 0 0 .25rem; font-size: 1.5rem; }
.page-header p { margin: 0; color: var(--p-text-muted-color); }
.header-actions { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
.table-toolbar { display: flex; gap: .75rem; align-items: center; margin-bottom: .75rem; flex-wrap: wrap; }
.empty-message { text-align: center; padding: 2rem; color: var(--p-text-muted-color); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-field { display: flex; flex-direction: column; gap: .35rem; }
.form-field.full { grid-column: 1 / -1; }
.form-field label { font-weight: 600; font-size: .85rem; }
.required { color: var(--grc-danger); }
.switch-row { padding-top: .35rem; }
.text-muted { color: var(--p-text-muted-color); font-size: .8rem; }
.text-success { color: var(--grc-success); }
.dialog-content { padding-top: .25rem; }
@media (max-width: 720px) { .form-grid { grid-template-columns: 1fr; } }
</style>
