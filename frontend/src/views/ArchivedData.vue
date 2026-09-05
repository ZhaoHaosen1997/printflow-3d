<script setup>
import { ref, onMounted, computed } from 'vue'
import { Trash2, AlertTriangle } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import { formatMoney as formatAmount, formatDateTime as formatTime, formatCategory } from '../utils/format'

const { get, del } = useApi()

const tab = ref('products')
const data = ref({ products: [], filaments: [], orders: [] })
const selected = ref({ products: [], filaments: [], orders: [] })
const loading = ref(false)
const deleting = ref(false)
const confirmVisible = ref(false)

const tabs = [
  { key: 'products', label: '商品' },
  { key: 'filaments', label: '耗材' },
  { key: 'orders', label: '订单' },
]

const currentList = computed(() => data.value[tab.value] || [])
const selectedIds = computed(() => selected.value[tab.value] || [])
const allSelected = computed(() =>
  currentList.value.length > 0 && selectedIds.value.length === currentList.value.length
)

const deleteCount = computed(() => {
  let c = 0
  for (const k of ['products', 'filaments', 'orders']) {
    c += (selected.value[k] || []).length
  }
  return c
})

async function fetchData() {
  loading.value = true
  try {
    data.value = await get('/api/admin/archived')
  } finally {
    loading.value = false
  }
}

function toggleSelect(id) {
  const arr = selected.value[tab.value]
  const idx = arr.indexOf(id)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(id)
}

function toggleAll() {
  if (allSelected.value) {
    selected.value[tab.value] = []
  } else {
    selected.value[tab.value] = currentList.value.map(i => i.id)
  }
}

function openConfirm() {
  if (deleteCount.value === 0) return
  confirmVisible.value = true
}

const ADMIN_TOKEN_KEY = 'printflow_admin_token'

function adminHeaders() {
  const token = localStorage.getItem(ADMIN_TOKEN_KEY)
  return token ? { 'X-Admin-Token': token } : undefined
}

// 服务端启用 ADMIN_TOKEN 时，403 提示后让用户输入一次并记住
async function delAdmin(body) {
  try {
    return await del('/api/admin/archived', body, adminHeaders())
  } catch (e) {
    if (!String(e.message).includes('X-Admin-Token')) throw e
    const input = prompt('本服务已启用管理令牌 (ADMIN_TOKEN)，请输入：')
    if (!input) throw e
    localStorage.setItem(ADMIN_TOKEN_KEY, input)
    return del('/api/admin/archived', body, { 'X-Admin-Token': input })
  }
}

async function doDelete() {
  deleting.value = true
  try {
    // 删除顺序：先订单 → 再耗材 → 最后商品（商品物理删除要求不再被订单明细/配方引用）
    for (const type of ['orders', 'filaments', 'products']) {
      const ids = selected.value[type]
      if (ids.length === 0) continue
      await delAdmin({ type, ids, confirm: 'DELETE' })
      selected.value[type] = []
    }
    confirmVisible.value = false
    await fetchData()
  } finally {
    deleting.value = false
  }
}

const totalCount = computed(() =>
  data.value.products.length + data.value.filaments.length + data.value.orders.length
)

onMounted(fetchData)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">归档数据管理</h2>
        <p class="text-sm text-gold-muted mt-1">
          共 {{ totalCount }} 条归档记录
        </p>
      </div>
      <button
        v-if="deleteCount > 0"
        class="flex items-center gap-2 px-4 py-2 bg-danger/10 text-danger border border-danger/30 rounded-lg
               hover:bg-danger/20 transition-colors text-sm"
        @click="openConfirm"
      >
        <Trash2 class="w-4 h-4" />
        永久删除 ({{ deleteCount }})
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-4 bg-dark-input rounded-lg p-1 w-fit">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors"
        :class="tab === t.key
          ? 'bg-dark-card text-gold shadow-sm'
          : 'text-gray-400 hover:text-gray-200'"
        @click="tab = t.key"
      >
        {{ t.label }}
        <span class="ml-1 text-xs opacity-60">({{ data[t.key]?.length || 0 }})</span>
      </button>
    </div>

    <!-- Table -->
    <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
      <div v-if="loading" class="px-4 py-12 text-center text-gray-500">加载中...</div>
      <div v-else-if="currentList.length === 0" class="px-4 py-12 text-center text-gray-500">
        暂无归档{{ tabs.find(t => t.key === tab)?.label }}
      </div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="border-b border-border-inner">
            <th class="px-4 py-3 w-10">
              <input
                type="checkbox"
                :checked="allSelected"
                class="w-4 h-4 rounded border-border-inner bg-dark-input accent-gold"
                @change="toggleAll"
              />
            </th>
            <th class="px-2 py-3 text-left text-xs text-gold-muted">名称/编号</th>
            <th v-if="tab !== 'orders'" class="px-2 py-3 text-left text-xs text-gold-muted">分类信息</th>
            <th class="px-2 py-3 text-right text-xs text-gold-muted">金额</th>
            <th class="px-2 py-3 text-right text-xs text-gold-muted">归档时间</th>
          </tr>
        </thead>
        <tbody>
          <!-- Products -->
          <template v-if="tab === 'products'">
            <tr
              v-for="p in currentList"
              :key="p.id"
              class="border-b border-border-inner/30 hover:bg-dark-input/30 transition-colors"
              :class="{ 'bg-gold/5': selectedIds.includes(p.id) }"
            >
              <td class="px-4 py-3">
                <input
                  type="checkbox"
                  :checked="selectedIds.includes(p.id)"
                  class="w-4 h-4 rounded border-border-inner bg-dark-input accent-gold"
                  @change="toggleSelect(p.id)"
                />
              </td>
              <td class="px-2 py-3 text-gray-200">{{ p.name }}</td>
              <td class="px-2 py-3 text-gray-400 text-xs">{{ categoryLabel(p.category) }}</td>
              <td class="px-2 py-3 text-right text-gray-200">{{ formatAmount(p.price_single) }}</td>
              <td class="px-2 py-3 text-right text-gray-500 text-xs">{{ formatTime(p.archived_at) }}</td>
            </tr>
          </template>

          <!-- Filaments -->
          <template v-if="tab === 'filaments'">
            <tr
              v-for="f in currentList"
              :key="f.id"
              class="border-b border-border-inner/30 hover:bg-dark-input/30 transition-colors"
              :class="{ 'bg-gold/5': selectedIds.includes(f.id) }"
            >
              <td class="px-4 py-3">
                <input
                  type="checkbox"
                  :checked="selectedIds.includes(f.id)"
                  class="w-4 h-4 rounded border-border-inner bg-dark-input accent-gold"
                  @change="toggleSelect(f.id)"
                />
              </td>
              <td class="px-2 py-3 text-gray-200">{{ f.display_name }}</td>
              <td class="px-2 py-3 text-gray-400 text-xs">{{ f.material }}</td>
              <td class="px-2 py-3 text-right text-gray-200">¥{{ f.price_per_kg }}/kg</td>
              <td class="px-2 py-3 text-right text-gray-500 text-xs">{{ formatTime(f.archived_at) }}</td>
            </tr>
          </template>

          <!-- Orders -->
          <template v-if="tab === 'orders'">
            <tr
              v-for="o in currentList"
              :key="o.id"
              class="border-b border-border-inner/30 hover:bg-dark-input/30 transition-colors"
              :class="{ 'bg-gold/5': selectedIds.includes(o.id) }"
            >
              <td class="px-4 py-3">
                <input
                  type="checkbox"
                  :checked="selectedIds.includes(o.id)"
                  class="w-4 h-4 rounded border-border-inner bg-dark-input accent-gold"
                  @change="toggleSelect(o.id)"
                />
              </td>
              <td class="px-2 py-3">
                <div class="text-gray-200 font-mono text-xs">{{ o.order_no }}</div>
                <div v-if="o.buyer_nickname" class="text-gray-500 text-xs">{{ o.buyer_nickname }}</div>
              </td>
              <td class="px-2 py-3 text-right text-gray-200">{{ formatAmount(o.actual_amount) }}</td>
              <td class="px-2 py-3 text-right text-gray-500 text-xs">{{ formatTime(o.archived_at) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Confirm Modal -->
    <Teleport to="body">
      <div
        v-if="confirmVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="confirmVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-md mx-4">
          <div class="flex items-center gap-3 px-6 py-4 border-b border-danger/30">
            <AlertTriangle class="w-6 h-6 text-danger" />
            <h3 class="text-lg font-serif text-danger">确认永久删除</h3>
          </div>
          <div class="px-6 py-4">
            <p class="text-gray-300 text-sm">
              即将永久删除 <span class="text-danger font-bold">{{ deleteCount }}</span> 条归档记录。
            </p>
            <p class="text-gray-500 text-xs mt-2">此操作不可恢复，删除后数据将彻底丢失。</p>
          </div>
          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="confirmVisible = false"
            >取消</button>
            <button
              class="px-4 py-2 text-sm bg-danger text-white rounded-md hover:bg-danger/90
                     transition-colors disabled:opacity-50"
              :disabled="deleting"
              @click="doDelete"
            >{{ deleting ? '删除中...' : '确认删除' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
