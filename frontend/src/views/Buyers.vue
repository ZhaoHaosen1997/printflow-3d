<script setup>
import { ref, onMounted, computed } from 'vue'
import { Search, X, Edit, User, MapPin, ShoppingBag, Calendar } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import SemanticBadge, { toneClasses } from '../components/SemanticBadge.vue'

const { loading, get, put } = useApi()

const buyers = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const searchQuery = ref('')

const detailVisible = ref(false)
const selectedBuyer = ref(null)
const buyerOrders = ref([])

const editModalVisible = ref(false)
const editingBuyer = ref(null)
const saving = ref(false)

const tagOptions = [
  { value: '老客户', label: '老客户', tone: 'info' },
  { value: '大户', label: '大户', tone: 'success' },
  { value: '好评', label: '好评', tone: 'success' },
  { value: '问题客户', label: '问题客户', tone: 'danger' },
]

const editForm = ref({
  tags: [],
  notes: '',
  province: '',
})

const columns = [
  { key: 'nickname', label: '买家昵称', sortable: true, mobileLabel: '昵称' },
  { key: 'province', label: '省份', mobileHidden: true },
  { key: 'total_orders', label: '累计订单', mobileLabel: '订单' },
  { key: 'total_amount', label: '累计消费', mobileLabel: '消费' },
  { key: 'tags', label: '标签', mobileHidden: true },
  { key: 'last_order_time', label: '最近下单', sortable: true, mobileLabel: '最近' },
]

const statusConfig = {
  pending_ship: { label: '待发货', tone: 'warning' },
  shipped: { label: '已发货', tone: 'info' },
  completed: { label: '交易成功', tone: 'success' },
  cancelled: { label: '已取消', tone: 'neutral' },
  returned: { label: '退货', tone: 'danger' },
}

const actions = [
  { label: '详情', handler: openDetail, class: 'btn-outline' },
  { label: '编辑', handler: openEdit, class: 'btn-soft' },
]

async function fetchBuyers() {
  const params = new URLSearchParams({ page: page.value, page_size: pageSize })
  if (searchQuery.value) params.set('search', searchQuery.value)
  const res = await get(`/api/buyers?${params}`)
  buyers.value = res.items
  total.value = res.total
}

function doSearch() {
  page.value = 1
  fetchBuyers()
}

async function openDetail(row) {
  const data = await get(`/api/buyers/${row.id}`)
  selectedBuyer.value = data
  buyerOrders.value = data.recent_orders || []
  detailVisible.value = true
}

function openEdit(row) {
  editingBuyer.value = row
  editForm.value = {
    tags: row.tags || [],
    notes: row.notes || '',
    province: row.province || '',
  }
  editModalVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const updated = await put(`/api/buyers/${editingBuyer.value.id}`, {
      tags: editForm.value.tags,
      notes: editForm.value.notes || null,
      province: editForm.value.province || null,
    })
    const idx = buyers.value.findIndex(b => b.id === editingBuyer.value.id)
    if (idx >= 0) buyers.value[idx] = { ...buyers.value[idx], ...updated }
    editModalVisible.value = false
  } finally {
    saving.value = false
  }
}

function toggleTag(tag) {
  const idx = editForm.value.tags.indexOf(tag)
  if (idx >= 0) {
    editForm.value.tags.splice(idx, 1)
  } else {
    editForm.value.tags.push(tag)
  }
}

function formatTime(val) {
  if (!val) return '-'
  if (typeof val === 'string') return val.slice(0, 16).replace('T', ' ')
  return val
}

function formatAmount(val) {
  if (val == null) return '-'
  return `¥${Number(val).toFixed(2)}`
}

function getTagTone(tag) {
  return tagOptions.find(t => t.value === tag)?.tone || 'neutral'
}

onMounted(fetchBuyers)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">买家管理</h2>
        <p class="text-sm text-gold-muted mt-1">共 {{ total }} 位买家</p>
      </div>
    </div>

    <!-- Search bar -->
    <div class="flex gap-2 mb-4">
      <div class="relative flex-1 max-w-sm">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索买家昵称..."
          class="w-full pl-10 pr-4 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                 focus:outline-none focus:border-gold/50 placeholder-gray-600"
          @keyup.enter="doSearch"
        />
      </div>
      <button
        class="px-4 py-2 text-sm bg-dark-card border border-border-inner text-gray-400 rounded-md
               hover:text-gray-200 hover:bg-dark-input transition-colors"
        @click="doSearch"
      >
        搜索
      </button>
    </div>

    <DataTable
      :columns="columns"
      :data="buyers"
      :loading="loading"
      :actions="actions"
      empty-text="暂无买家数据"
    >
      <template #cell-nickname="{ value }">
        <span class="text-gray-200 font-medium">{{ value }}</span>
      </template>
      <template #cell-province="{ value }">
        <span class="text-gray-400 text-sm">{{ value || '-' }}</span>
      </template>
      <template #cell-total_orders="{ value }">
        <span class="text-gray-200">{{ value || 0 }}笔</span>
      </template>
      <template #cell-total_amount="{ value }">
        <span class="text-gray-200">{{ formatAmount(value) }}</span>
      </template>
      <template #cell-tags="{ value }">
        <div class="flex flex-wrap gap-1">
          <SemanticBadge
            v-for="tag in (value || [])"
            :key="tag"
            :tone="getTagTone(tag)"
            :label="tag"
          />
          <span v-if="!value || value.length === 0" class="text-gray-600 text-xs">-</span>
        </div>
      </template>
      <template #cell-last_order_time="{ value }">
        <span class="text-gray-500 text-sm">{{ formatTime(value) }}</span>
      </template>
    </DataTable>

    <!-- Pagination -->
    <div v-if="total > pageSize" class="flex items-center justify-between mt-4 text-sm">
      <span class="text-gray-500">
        第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页
      </span>
      <div class="flex gap-2">
        <button
          class="px-3 py-1.5 rounded-md bg-dark-card border border-border-inner text-gray-400
                 hover:text-gray-200 hover:bg-dark-input transition-colors disabled:opacity-40"
          :disabled="page <= 1"
          @click="page--; fetchBuyers()"
        >上一页</button>
        <button
          class="px-3 py-1.5 rounded-md bg-dark-card border border-border-inner text-gray-400
                 hover:text-gray-200 hover:bg-dark-input transition-colors disabled:opacity-40"
          :disabled="page * pageSize >= total"
          @click="page++; fetchBuyers()"
        >下一页</button>
      </div>
    </div>

    <!-- Detail Slide-over -->
    <Teleport to="body">
      <div
        v-if="detailVisible"
        class="fixed inset-0 z-50 flex justify-end"
        @click.self="detailVisible = false"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
        <div class="relative w-full md:max-w-lg bg-dark-card md:border-l border-border-main shadow-2xl overflow-y-auto">
          <div class="sticky top-0 bg-dark-card border-b border-border-inner px-4 md:px-6 py-4 flex items-center justify-between z-10">
            <h3 class="text-lg font-serif text-gold-title">买家详情</h3>
            <button class="text-gray-500 hover:text-gray-300" @click="detailVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <div v-if="selectedBuyer" class="p-6 space-y-6">
            <!-- Buyer info card -->
            <div class="bg-dark-input rounded-lg p-4 border border-border-inner space-y-3">
              <div class="flex items-center gap-2">
                <User class="w-4 h-4 text-gold-muted" />
                <span class="text-gray-200 font-medium text-lg">{{ selectedBuyer.nickname }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-gray-400">
                <MapPin class="w-3.5 h-3.5" />
                {{ selectedBuyer.province || '未知省份' }}
              </div>
              <div class="grid grid-cols-2 gap-3 pt-2 border-t border-border-inner/50">
                <div>
                  <div class="text-xs text-gray-500">累计订单</div>
                  <div class="text-gray-200 font-medium">{{ selectedBuyer.total_orders }} 笔</div>
                </div>
                <div>
                  <div class="text-xs text-gray-500">累计消费</div>
                  <div class="text-gray-200 font-medium">{{ formatAmount(selectedBuyer.total_amount) }}</div>
                </div>
                <div>
                  <div class="text-xs text-gray-500">首单时间</div>
                  <div class="text-gray-200 text-sm">{{ formatTime(selectedBuyer.first_order_time) }}</div>
                </div>
                <div>
                  <div class="text-xs text-gray-500">最近下单</div>
                  <div class="text-gray-200 text-sm">{{ formatTime(selectedBuyer.last_order_time) }}</div>
                </div>
              </div>
              <div v-if="selectedBuyer.tags && selectedBuyer.tags.length" class="pt-2 border-t border-border-inner/50">
                <div class="text-xs text-gray-500 mb-2">标签</div>
                <div class="flex flex-wrap gap-1">
                  <SemanticBadge
                    v-for="tag in selectedBuyer.tags"
                    :key="tag"
                    :tone="getTagTone(tag)"
                    :label="tag"
                  />
                </div>
              </div>
              <div v-if="selectedBuyer.notes" class="pt-2 border-t border-border-inner/50">
                <div class="text-xs text-gray-500 mb-1">备注</div>
                <div class="text-gray-300 text-sm">{{ selectedBuyer.notes }}</div>
              </div>
            </div>

            <!-- Recent orders -->
            <div>
              <h4 class="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <ShoppingBag class="w-4 h-4" />
                最近订单（{{ buyerOrders.length }} 笔）
              </h4>
              <div v-if="buyerOrders.length === 0" class="text-center py-6 text-gray-500 text-sm">
                暂无订单
              </div>
              <div v-else class="border border-border-inner rounded-lg overflow-hidden">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-border-inner bg-dark-input/50">
                      <th class="px-3 py-2 text-left text-xs text-gold-muted">订单编号</th>
                      <th class="px-3 py-2 text-left text-xs text-gold-muted">状态</th>
                      <th class="px-3 py-2 text-right text-xs text-gold-muted">金额</th>
                      <th class="px-3 py-2 text-right text-xs text-gold-muted">时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="o in buyerOrders"
                      :key="o.id"
                      class="border-b border-border-inner/30 hover:bg-dark-input/30 transition-colors"
                    >
                      <td class="px-3 py-2 text-gray-300 font-mono text-xs">{{ o.order_no }}</td>
                      <td class="px-3 py-2">
                        <SemanticBadge :tone="statusConfig[o.status]?.tone" :label="statusConfig[o.status]?.label || o.status" />
                      </td>
                      <td class="px-3 py-2 text-right text-gray-200">{{ formatAmount(o.actual_amount) }}</td>
                      <td class="px-3 py-2 text-right text-gray-500 text-xs">{{ formatTime(o.order_time) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div
        v-if="editModalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="editModalVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-md mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">编辑买家 — {{ editingBuyer?.nickname }}</h3>
            <button class="text-gray-500 hover:text-gray-300" @click="editModalVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <div class="px-6 py-4 space-y-4">
            <!-- Tags -->
            <div>
              <label class="block text-sm text-gray-400 mb-2">标签</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="tag in tagOptions"
                  :key="tag.value"
                  class="px-3 py-1.5 rounded-md text-xs font-medium border transition-colors"
                  :class="editForm.tags.includes(tag.value)
                    ? toneClasses[tag.tone] + ' border-current'
                    : 'bg-dark-input border-border-inner text-gray-500 hover:text-gray-300'"
                  @click="toggleTag(tag.value)"
                >
                  {{ tag.label }}
                </button>
              </div>
            </div>

            <!-- Province -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">省份</label>
              <input
                v-model="editForm.province"
                type="text"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
                placeholder="如：江苏省"
              />
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">备注</label>
              <textarea
                v-model="editForm.notes"
                rows="3"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600 resize-none"
                placeholder="买家备注..."
              ></textarea>
            </div>
          </div>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="editModalVisible = false"
            >取消</button>
            <button
              class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                     hover:bg-gold/30 transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleSave"
            >{{ saving ? '保存中...' : '保存' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
