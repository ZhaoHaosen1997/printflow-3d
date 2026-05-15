<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, Pencil, Archive } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import FormModal from '../components/FormModal.vue'
import StatusBadge from '../components/StatusBadge.vue'

const { loading, get, post, put, del } = useApi()

const filaments = ref([])
const modalVisible = ref(false)
const editingFilament = ref(null)
const saving = ref(false)

const activeFilaments = computed(() => filaments.value.filter(f => f.status === 'active'))

const columns = [
  { key: 'display_name', label: '显示名称', sortable: true },
  { key: 'brand', label: '品牌', sortable: true },
  { key: 'material', label: '材料' },
  { key: 'price_per_kg', label: '单价/kg' },
  { key: 'status', label: '状态' },
]

const actions = [
  { label: '编辑', handler: editFilament },
  {
    label: '归档',
    handler: archiveFilament,
    condition: (row) => row.status === 'active',
  },
]

const materialOptions = [
  { value: 'PLA', label: 'PLA' },
  { value: 'PETG', label: 'PETG' },
  { value: 'ABS', label: 'ABS' },
  { value: '树脂', label: '树脂' },
]

const fields = [
  { name: 'brand', label: '品牌', type: 'text', required: true, placeholder: '如 eSun, 三绿, Bambu' },
  { name: 'material', label: '材料', type: 'select', required: true, options: materialOptions },
  {
    name: 'price_per_kg', label: '每kg价格 (元)', type: 'number', required: true,
    placeholder: '如 60', hint: '价格变动将自动更新关联商品的材料成本',
  },
]

async function fetchFilaments() {
  filaments.value = await get('/api/filaments')
}

function openCreate() {
  editingFilament.value = null
  modalVisible.value = true
}

function editFilament(row) {
  editingFilament.value = row
  modalVisible.value = true
}

async function archiveFilament(row) {
  if (!confirm(`确定归档耗材 "${row.brand} ${row.material}"？`)) return
  try {
    await del(`/api/filaments/${row.id}`)
    row.status = 'archived'
  } catch {}
}

async function handleSubmit(data) {
  saving.value = true
  try {
    if (editingFilament.value) {
      const updated = await put(`/api/filaments/${editingFilament.value.id}`, data)
      const idx = filaments.value.findIndex(f => f.id === editingFilament.value.id)
      if (idx >= 0) filaments.value[idx] = updated
    } else {
      const created = await post('/api/filaments', data)
      filaments.value.push(created)
    }
    modalVisible.value = false
  } finally {
    saving.value = false
  }
}

onMounted(fetchFilaments)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">耗材管理</h2>
        <p class="text-sm text-gold-muted mt-1">管理打印耗材品牌和价格，用于配方成本计算</p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
               hover:bg-gold/30 transition-colors text-sm"
        @click="openCreate"
      >
        <Plus class="w-4 h-4" />
        新增耗材
      </button>
    </div>

    <DataTable
      :columns="columns"
      :data="activeFilaments"
      :loading="loading"
      :actions="actions"
      empty-text="暂无耗材，请点击「新增耗材」创建"
    >
      <template #cell-price_per_kg="{ value }">
        <span class="text-gold-price font-medium">¥{{ Number(value).toFixed(2) }}</span>
      </template>
      <template #cell-status="{ value }">
        <StatusBadge :status="value" />
      </template>
    </DataTable>

    <FormModal
      :visible="modalVisible"
      :title="editingFilament ? '编辑耗材' : '新增耗材'"
      :fields="fields"
      :initial-data="editingFilament || {}"
      :loading="saving"
      @close="modalVisible = false"
      @submit="handleSubmit"
    />
  </div>
</template>
