<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, X } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import ModalShell from '../components/ModalShell.vue'
import SemanticBadge from '../components/SemanticBadge.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { TASK_STATUS } from '../constants/orderStatus'
import { formatDateTime as formatTime } from '../utils/format'

const { loading, get, post, put } = useApi()

const tasks = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref('')

const createModalVisible = ref(false)
const creating = ref(false)
const products = ref([])
const selectedRecipeId = ref(null)
const newTaskNotes = ref('')

const STATUS_TONES = { pending: 'neutral', printing: 'info', done: 'success', failed: 'danger', cancelled: 'warning' }
const statusConfig = Object.fromEntries(
  Object.entries(TASK_STATUS).map(([key, label]) => [key, { tone: STATUS_TONES[key], label }])
)

const statusTabs = [
  { value: '', label: '全部' },
  { value: 'pending', label: '待处理' },
  { value: 'printing', label: '打印中' },
  { value: 'done', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'cancelled', label: '已取消' },
]

const columns = [
  { key: 'task_no', label: '任务编号', sortable: true, mobileLabel: '编号' },
  { key: 'product_name', label: '商品', sortable: true, mobileLabel: '商品' },
  { key: 'recipe_name', label: '配方', mobileHidden: true },
  { key: 'output_qty', label: '产出数量', mobileLabel: '产出' },
  { key: 'status', label: '状态', mobileLabel: '状态' },
  { key: 'print_time_min', label: '预估时长', mobileHidden: true },
  { key: 'created_at', label: '创建时间', sortable: true, mobileLabel: '创建' },
]

const actions = [
  { label: '开始', handler: row => startTask(row.id), class: 'btn-soft', condition: row => row.status === 'pending' },
  { label: '完成', handler: row => completeTask(row.id), class: 'btn-filled', condition: row => row.status === 'printing' },
  { label: '失败', handler: row => failTask(row.id), class: 'btn-danger-outline', condition: row => row.status === 'printing' },
  { label: '取消', handler: row => cancelTask(row.id), class: 'btn-ghost', condition: row => row.status === 'pending' || row.status === 'printing' },
]

const flatRecipes = computed(() => {
  const result = []
  for (const p of products.value) {
    for (const r of (p.recipes || [])) {
      if (r.status === 'active') {
        result.push({ ...r, product_name: p.name, product_category: p.category })
      }
    }
  }
  return result
})

async function fetchTasks() {
  const params = new URLSearchParams({ page: page.value, page_size: pageSize })
  if (statusFilter.value) params.set('status', statusFilter.value)
  const res = await get(`/api/print-tasks?${params}`)
  tasks.value = res.items
  total.value = res.total
}

async function fetchProducts() {
  products.value = await get('/api/products')
}

function changeFilter(s) {
  statusFilter.value = s
  page.value = 1
  fetchTasks()
}

function openCreate() {
  selectedRecipeId.value = null
  newTaskNotes.value = ''
  createModalVisible.value = true
}

async function handleCreate() {
  if (!selectedRecipeId.value) return
  creating.value = true
  try {
    await post('/api/print-tasks', {
      recipe_id: selectedRecipeId.value,
      notes: newTaskNotes.value || null,
    })
    createModalVisible.value = false
    await fetchTasks()
  } finally {
    creating.value = false
  }
}

async function startTask(id) {
  try {
    await post(`/api/print-tasks/${id}/start`)
    await fetchTasks()
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

async function completeTask(id) {
  try {
    await post(`/api/print-tasks/${id}/complete`)
    await fetchTasks()
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

async function failTask(id) {
  try {
    await post(`/api/print-tasks/${id}/fail`, { fail_reason: null })
    await fetchTasks()
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

async function cancelTask(id) {
  try {
    await post(`/api/print-tasks/${id}/cancel`)
    await fetchTasks()
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

function formatPrintTime(val) {
  if (val == null) return '-'
  if (val < 60) return `${val}分钟`
  const h = Math.floor(val / 60)
  const m = val % 60
  return m > 0 ? `${h}小时${m}分钟` : `${h}小时`
}

const recipeList = computed(() => {
  return flatRecipes.value.map(r => ({
    ...r,
    displayLabel: `${r.product_name} — ${r.name} (产出${r.output_qty}件${r.print_time_min ? ', ' + formatPrintTime(r.print_time_min) : ''})`,
  }))
})

const selectedRecipe = computed(() =>
  flatRecipes.value.find(r => r.id === selectedRecipeId.value)
)

onMounted(() => {
  fetchTasks()
  fetchProducts()
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">打印任务</h2>
        <p class="text-sm text-gold-muted mt-1">共 {{ total }} 个任务</p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
               hover:bg-gold/30 transition-colors text-sm"
        @click="openCreate"
      >
        <Plus class="w-4 h-4" />
        创建任务
      </button>
    </div>

    <!-- Status tabs -->
    <div class="flex gap-2 mb-4 flex-wrap">
      <button
        v-for="t in statusTabs"
        :key="t.value"
        class="px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
        :class="statusFilter === t.value
          ? 'bg-gold/20 text-gold border border-gold/30'
          : 'bg-dark-card text-gray-400 border border-border-inner hover:text-gray-200 hover:bg-dark-input'"
        @click="changeFilter(t.value)"
      >
        {{ t.label }}
      </button>
    </div>

    <DataTable
      :columns="columns"
      :data="tasks"
      :loading="loading"
      :actions="actions"
      empty-text="暂无打印任务"
    >
      <template #cell-task_no="{ value }">
        <span class="font-mono text-sm text-gray-200">{{ value }}</span>
      </template>
      <template #cell-product_name="{ value }">
        <span class="text-gray-200">{{ value || '-' }}</span>
      </template>
      <template #cell-recipe_name="{ value }">
        <span class="text-gray-400 text-sm">{{ value || '-' }}</span>
      </template>
      <template #cell-output_qty="{ value }">
        <span class="text-gray-200">{{ value || '-' }}</span>
      </template>
      <template #cell-status="{ value }">
        <SemanticBadge :tone="statusConfig[value]?.tone" :label="statusConfig[value]?.label || value" />
      </template>
      <template #cell-print_time_min="{ value }">
        <span class="text-gray-400 text-sm">{{ formatPrintTime(value) }}</span>
      </template>
      <template #cell-created_at="{ value }">
        <span class="text-gray-500 text-sm">{{ formatTime(value) }}</span>
      </template>
    </DataTable>

    <!-- Pagination -->
    <PaginationBar
      v-if="total > pageSize"
      :page="page"
      :total-pages="Math.ceil(total / pageSize)"
      :total="total"
      unit="个任务"
      @go="p => { page = p; fetchTasks() }"
    />

    <!-- Create Modal -->
    <ModalShell
      v-if="createModalVisible"
      title="创建打印任务"
      width="max-w-lg"
      @close="createModalVisible = false"
    >

          <div class="px-6 py-4 space-y-4">
            <div>
              <label class="block text-sm text-gray-400 mb-1">选择配方 <span class="text-danger">*</span></label>
              <select
                v-model="selectedRecipeId"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50"
              >
                <option :value="null" disabled>请选择配方...</option>
                <optgroup
                  v-for="p in products"
                  :key="p.id"
                  :label="p.name"
                >
                  <option
                    v-for="r in (p.recipes || []).filter(r => r.status === 'active')"
                    :key="r.id"
                    :value="r.id"
                  >
                    {{ r.name }}（产出{{ r.output_qty }}件{{ r.print_time_min ? '，' + formatPrintTime(r.print_time_min) : '' }}）
                  </option>
                </optgroup>
              </select>
            </div>

            <div v-if="selectedRecipe">
              <div class="text-xs text-gray-500 space-y-1 bg-dark-input rounded-md p-3 border border-border-inner">
                <div><span class="text-gray-400">商品：</span>{{ selectedRecipe.product_name }}</div>
                <div><span class="text-gray-400">产出数量：</span>{{ selectedRecipe.output_qty }} 件</div>
                <div v-if="selectedRecipe.print_time_min">
                  <span class="text-gray-400">预估时长：</span>{{ formatPrintTime(selectedRecipe.print_time_min) }}
                </div>
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">备注</label>
              <textarea
                v-model="newTaskNotes"
                rows="2"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600 resize-none"
                placeholder="可选备注..."
              ></textarea>
            </div>
          </div>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="createModalVisible = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                     hover:bg-gold/30 transition-colors disabled:opacity-50"
              :disabled="!selectedRecipeId || creating"
              @click="handleCreate"
            >
              {{ creating ? '创建中...' : '创建任务' }}
            </button>
          </div>
    </ModalShell>
  </div>
</template>
