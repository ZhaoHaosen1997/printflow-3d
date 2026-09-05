<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, X } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import ModalShell from '../components/ModalShell.vue'
import StatusBadge from '../components/StatusBadge.vue'

const { loading, get, post, put, del } = useApi()

const filaments = ref([])
const modalVisible = ref(false)
const editingFilament = ref(null)
const saving = ref(false)

const form = ref({
  brand: '',
  material: '',
  price_per_kg: 0,
})

// Autocomplete: material suggestions from existing filaments
const materialInput = ref('')
const showMaterialSuggestions = ref(false)

const materialSuggestions = computed(() => {
  const materials = [...new Set(filaments.value.map(f => f.material).filter(Boolean))]
  if (!materialInput.value) return materials
  return materials.filter(m => m.toLowerCase().includes(materialInput.value.toLowerCase()))
})

function selectMaterialSuggestion(m) {
  form.value.material = m
  materialInput.value = m
  showMaterialSuggestions.value = false
}

const activeFilaments = computed(() => filaments.value.filter(f => f.status === 'active'))

const columns = [
  { key: 'display_name', label: '显示名称', sortable: true, mobileLabel: '名称' },
  { key: 'brand', label: '品牌', sortable: true, mobileHidden: true },
  { key: 'material', label: '材料', mobileLabel: '材料' },
  { key: 'price_per_kg', label: '单价/kg', mobileLabel: '单价' },
  { key: 'status', label: '状态', mobileLabel: '状态' },
]

const actions = [
  { label: '编辑', handler: editFilament, class: 'btn-outline' },
  { label: '归档', handler: archiveFilament, condition: (row) => row.status === 'active', class: 'btn-danger-outline' },
]

function resetForm() {
  form.value = { brand: '', material: '', price_per_kg: 0 }
  materialInput.value = ''
  showMaterialSuggestions.value = false
}

async function fetchFilaments() {
  filaments.value = await get('/api/filaments')
}

function openCreate() {
  editingFilament.value = null
  resetForm()
  modalVisible.value = true
}

function editFilament(row) {
  editingFilament.value = row
  form.value = {
    brand: row.brand,
    material: row.material,
    price_per_kg: row.price_per_kg,
  }
  materialInput.value = row.material
  showMaterialSuggestions.value = false
  modalVisible.value = true
}

async function archiveFilament(row) {
  if (!confirm(`确定归档耗材 "${row.brand} ${row.material}"？`)) return
  try {
    await del(`/api/filaments/${row.id}`)
    row.status = 'archived'
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

async function handleSubmit() {
  saving.value = true
  try {
    const payload = { ...form.value }
    if (editingFilament.value) {
      const updated = await put(`/api/filaments/${editingFilament.value.id}`, payload)
      const idx = filaments.value.findIndex(f => f.id === editingFilament.value.id)
      if (idx >= 0) filaments.value[idx] = updated
    } else {
      const created = await post('/api/filaments', payload)
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

    <!-- Custom Modal -->
    <ModalShell
      v-if="modalVisible"
      :title="editingFilament ? '编辑耗材' : '新增耗材'"
      width="max-w-lg"
      @close="modalVisible = false"
    >

          <form @submit.prevent="handleSubmit" class="px-6 py-4 space-y-4">
            <div>
              <label class="block text-sm text-gray-400 mb-1">品牌 <span class="text-danger">*</span></label>
              <input
                v-model="form.brand"
                type="text" required placeholder="如 eSun, 三绿, Bambu"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
            </div>

            <div class="relative">
              <label class="block text-sm text-gray-400 mb-1">材料 <span class="text-danger">*</span></label>
              <input
                v-model="materialInput"
                type="text" required placeholder="如 PLA, PETG, ABS..."
                autocomplete="off"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
                @focus="showMaterialSuggestions = true"
                @blur="setTimeout(() => showMaterialSuggestions = false, 150)"
                @input="form.material = materialInput; showMaterialSuggestions = true"
              />
              <div
                v-if="showMaterialSuggestions && materialSuggestions.length > 0"
                class="absolute z-10 top-full mt-1 w-full bg-dark-card border border-border-inner rounded-md shadow-lg max-h-40 overflow-y-auto"
              >
                <button
                  v-for="m in materialSuggestions"
                  :key="m"
                  type="button"
                  class="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-dark-input transition-colors"
                  @mousedown.prevent="selectMaterialSuggestion(m)"
                >
                  {{ m }}
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">每kg价格 (元) <span class="text-danger">*</span></label>
              <input
                v-model.number="form.price_per_kg"
                type="number" step="0.01" min="0" required placeholder="如 60"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
              <p class="text-xs text-gray-600 mt-1">价格变动将自动更新关联商品的材料成本</p>
            </div>
          </form>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="modalVisible = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                     hover:bg-gold/30 transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleSubmit"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
    </ModalShell>
  </div>
</template>
