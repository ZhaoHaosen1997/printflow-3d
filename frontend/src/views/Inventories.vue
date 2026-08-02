<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, X, Check } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import SemanticBadge from '../components/SemanticBadge.vue'

const { loading, get, put, post } = useApi()

const inventories = ref([])
const modalVisible = ref(false)
const editingItem = ref(null)
const saving = ref(false)

const form = ref({
  quantity: 0,
  warning_threshold: 5,
})

const categoryMap = {
  counter: '计数器',
  token: '指示物',
  other: '其他',
  bundle: '合集',
}

const stats = computed(() => {
  const total = inventories.value.length
  const outOfStock = inventories.value.filter(i => i.quantity === 0).length
  const lowStock = inventories.value.filter(i => i.quantity > 0 && i.quantity <= i.warning_threshold).length
  return { total, outOfStock, lowStock }
})

const columns = [
  { key: 'product_name', label: '商品名称', sortable: true, mobileLabel: '商品' },
  { key: 'product_category', label: '分类', sortable: true, mobileHidden: true },
  { key: 'quantity', label: '当前库存', mobileLabel: '库存' },
  { key: 'warning_threshold', label: '预警阈值', mobileLabel: '阈值' },
  { key: 'stock_status', label: '状态', mobileLabel: '状态' },
]

const actions = [
  { label: '调整库存', handler: openEdit, class: 'btn-outline' },
]

function resetForm() {
  form.value = { quantity: 0, warning_threshold: 5 }
}

async function fetchInventories() {
  inventories.value = await get('/api/inventories')
}

function openEdit(row) {
  editingItem.value = row
  form.value = {
    quantity: row.quantity,
    warning_threshold: row.warning_threshold,
  }
  modalVisible.value = true
}

async function handleSubmit() {
  saving.value = true
  try {
    const updated = await put(`/api/inventories/${editingItem.value.id}`, {
      quantity: form.value.quantity,
      warning_threshold: form.value.warning_threshold,
    })
    const idx = inventories.value.findIndex(i => i.id === editingItem.value.id)
    if (idx >= 0) {
      inventories.value[idx] = { ...inventories.value[idx], ...updated }
    }
    modalVisible.value = false
  } finally {
    saving.value = false
  }
}

async function ensureAll() {
  try {
    await post('/api/inventories/ensure-all')
    await fetchInventories()
  } catch (e) {
    alert('同步库存失败: ' + (e.message || e))
  }
}

function stockStatus(row) {
  if (row.quantity === 0) return 'out'
  if (row.quantity <= row.warning_threshold) return 'low'
  return 'normal'
}

const stockToneMap = { out: 'danger', low: 'warning', normal: 'success' }
const stockLabelMap = { out: '缺货', low: '不足', normal: '充足' }
function stockTone(row) {
  return stockToneMap[stockStatus(row)]
}
function stockLabel(row) {
  return stockLabelMap[stockStatus(row)]
}

onMounted(fetchInventories)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">库存管理</h2>
        <p class="text-sm text-gold-muted mt-1">
          共 {{ stats.total }} 个商品 ·
          <span class="text-danger">{{ stats.outOfStock }} 个缺货</span> ·
          <span class="text-warning">{{ stats.lowStock }} 个库存不足</span>
        </p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
               hover:bg-gold/30 transition-colors text-sm"
        @click="ensureAll"
      >
        <Check class="w-4 h-4" />
        一键盘点
      </button>
    </div>

    <DataTable
      :columns="columns"
      :data="inventories"
      :loading="loading"
      :actions="actions"
      empty-text="暂无可管理的库存"
    >
      <template #cell-product_category="{ value }">
        <span class="text-gray-400">{{ categoryMap[value] || value }}</span>
      </template>
      <template #cell-quantity="{ row }">
        <span
          class="font-medium text-sm"
          :class="{
            'text-danger': stockStatus(row) === 'out',
            'text-warning': stockStatus(row) === 'low',
            'text-gray-200': stockStatus(row) === 'normal',
          }"
        >
          {{ row.quantity }}
        </span>
      </template>
      <template #cell-warning_threshold="{ value }">
        <span class="text-gray-400">{{ value }}</span>
      </template>
      <template #cell-stock_status="{ row }">
        <SemanticBadge :tone="stockTone(row)" :label="stockLabel(row)" />
      </template>
    </DataTable>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div
        v-if="modalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="modalVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-md mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">
              调整库存 — {{ editingItem?.product_name }}
            </h3>
            <button class="text-gray-500 hover:text-gray-300" @click="modalVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="px-6 py-4 space-y-4">
            <div>
              <label class="block text-sm text-gray-400 mb-1">当前库存数量 <span class="text-danger">*</span></label>
              <input
                v-model.number="form.quantity"
                type="number" min="0" required
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
            </div>
            <div>
              <label class="block text-sm text-gray-400 mb-1">预警阈值</label>
              <input
                v-model.number="form.warning_threshold"
                type="number" min="1" required
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
              <p class="text-xs text-gray-600 mt-1">库存 ≤ 阈值时将标记为"不足"</p>
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
        </div>
      </div>
    </Teleport>
  </div>
</template>
