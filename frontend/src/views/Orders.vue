<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, X, Search, Download } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const { loading, get, post, put, del } = useApi()

const orders = ref([])
const totalOrders = ref(0)
const currentPage = ref(1)
const pageSize = ref(30)
const products = ref([])

const statuses = [
  { value: '', label: '全部状态' },
  { value: 'pending_ship', label: '待发货' },
  { value: 'shipped', label: '已发货' },
  { value: 'completed', label: '交易成功' },
  { value: 'cancelled', label: '已取消' },
  { value: 'returned', label: '退货' },
]

const filters = ref({
  status: '',
  xianyu_order_id: '',
  product_id: '',
  date_from: '',
  date_to: '',
})

const totalPages = computed(() => Math.max(1, Math.ceil(totalOrders.value / pageSize.value)))

const columns = [
  { key: 'order_no', label: '订单编号', sortable: true },
  { key: 'xianyu_order_id', label: '闲鱼订单号' },
  { key: 'status', label: '状态' },
  { key: 'buyer_nickname', label: '买家' },
  { key: 'total_amount', label: '原价' },
  { key: 'actual_amount', label: '实付' },
  { key: 'source', label: '来源' },
  { key: 'order_time', label: '下单时间', sortable: true },
  { key: 'completed_time', label: '完成时间' },
]

const orderActions = [
  { label: '查看/编辑', handler: editOrder, class: 'btn-outline' },
  { label: '发货', handler: shipOrder, condition: (r) => r.status === 'pending_ship', class: 'btn-soft' },
  { label: '完成', handler: completeOrder, condition: (r) => r.status === 'shipped', class: 'btn-filled' },
  { label: '取消', handler: cancelOrder, condition: (r) => r.status !== 'cancelled' && r.status !== 'completed' && r.status !== 'returned' && r.status !== 'archived', class: 'btn-danger-outline' },
  { label: '归档', handler: archiveOrder, condition: (r) => r.status === 'completed' || r.status === 'cancelled' || r.status === 'returned', class: 'btn-danger-outline' },
]

const modalVisible = ref(false)
const editingOrder = ref(null)
const orderSaving = ref(false)

const orderForm = ref({
  order_time: '',
  actual_amount: null,
  shipping_fee: null,
  packaging_fee: null,
  service_fee: null,
  service_fee_rate: null,
  charity_fee: null,
  charity_fee_rate: null,
  notes: '',
  buyer_nickname: '',
  items: [],
})

async function fetchAll() {
  const offset = (currentPage.value - 1) * pageSize.value
  let params = `?limit=${pageSize.value}&offset=${offset}`
  const f = filters.value
  if (f.status) params += `&status=${encodeURIComponent(f.status)}`
  if (f.xianyu_order_id) params += `&xianyu_order_id=${encodeURIComponent(f.xianyu_order_id)}`
  if (f.product_id) params += `&product_id=${f.product_id}`
  if (f.date_from) params += `&date_from=${f.date_from}`
  if (f.date_to) params += `&date_to=${f.date_to}`
  const [ordData, prod] = await Promise.all([
    get(`/api/orders${params}`),
    get('/api/products'),
  ])
  orders.value = ordData.items
  totalOrders.value = ordData.total
  products.value = prod.filter(p => p.status === 'active')
}

function applyFilters() {
  currentPage.value = 1
  fetchAll()
}

function clearFilters() {
  filters.value = { status: '', xianyu_order_id: '', product_id: '', date_from: '', date_to: '' }
  currentPage.value = 1
  fetchAll()
}

function goPage(page) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  fetchAll()
}

async function exportCSV() {
  const params = new URLSearchParams()
  const f = filters.value
  if (f.status) params.set('status', f.status)
  if (f.date_from) params.set('date_from', f.date_from)
  if (f.date_to) params.set('date_to', f.date_to)
  if (f.product_id) params.set('product_id', f.product_id)
  try {
    const res = await fetch(`/api/orders/export?${params}`)
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'orders_export.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) {
    alert('CSV导出失败，请重试')
  }
}

function resetForm() {
  orderForm.value = {
    order_time: new Date().toISOString().slice(0, 16),
    actual_amount: null,
    shipping_fee: null,
    packaging_fee: null,
    service_fee: null,
    service_fee_rate: null,
    charity_fee: null,
    charity_fee_rate: null,
    notes: '',
    buyer_nickname: '',
    items: [],
  }
}

function openCreate() {
  editingOrder.value = null
  resetForm()
  modalVisible.value = true
}

function editOrder(row) {
  editingOrder.value = row
  get(`/api/orders/${row.id}`).then(full => {
    orderForm.value = {
      order_time: full.order_time ? full.order_time.slice(0, 16) : '',
      actual_amount: full.actual_amount,
      shipping_fee: full.shipping_fee,
      packaging_fee: full.packaging_fee,
      service_fee: full.service_fee,
      service_fee_rate: full.service_fee_rate ? Number(full.service_fee_rate) * 100 : null,
      charity_fee: full.charity_fee != null ? Number(full.charity_fee) : null,
      charity_fee_rate: full.charity_fee_rate != null ? Number(full.charity_fee_rate) * 100 : null,
      notes: full.notes || '',
      buyer_nickname: full.buyer_nickname || '',
      items: (full.items || []).map(item => ({
        product_id: item.product_id,
        product_name: item.product_name || '',
        quantity: item.quantity,
        unit_price: item.unit_price,
        material_cost: item.material_cost,
      })),
    }
    modalVisible.value = true
  })
}

async function shipOrder(row) {
  if (!confirm(`确认发货 ${row.order_no}？`)) return
  await put(`/api/orders/${row.id}`, { status: 'shipped' })
  row.status = 'shipped'
}

async function completeOrder(row) {
  if (!confirm(`确认完成 ${row.order_no}？`)) return
  await put(`/api/orders/${row.id}`, { status: 'completed' })
  row.status = 'completed'
}

async function cancelOrder(row) {
  if (!confirm(`确定取消 ${row.order_no}？`)) return
  await del(`/api/orders/${row.id}`)
  row.status = 'cancelled'
}

async function archiveOrder(row) {
  if (!confirm(`确定归档 ${row.order_no}？归档后将从活跃列表隐藏。`)) return
  await put(`/api/orders/${row.id}`, { status: 'archived' })
  row.status = 'archived'
}

function addOrderItem() {
  orderForm.value.items.push({
    product_id: null,
    product_name: '',
    quantity: 1,
    unit_price: 0,
    material_cost: 0,
  })
}

function removeOrderItem(idx) {
  orderForm.value.items.splice(idx, 1)
  recalcTotal()
}

function onItemProductChange(idx) {
  const item = orderForm.value.items[idx]
  const prod = products.value.find(p => p.id === Number(item.product_id))
  if (prod) {
    item.product_name = prod.name
    item.unit_price = Number(prod.price_single)
    item.material_cost = Number(prod.material_cost)
    if (prod.charity_rate != null && orderForm.value.charity_fee_rate == null) {
      orderForm.value.charity_fee_rate = Number(prod.charity_rate) * 100
    }
    recalcTotal()
  }
}

function recalcTotal() {
  let total = 0
  for (const item of orderForm.value.items) {
    total += (Number(item.unit_price) || 0) * (Number(item.quantity) || 1)
  }
  // auto-calc actual = total if not explicitly set (null means untouched)
  if (orderForm.value.actual_amount == null) {
    orderForm.value.actual_amount = Math.round(total * 100) / 100
  }
}

const computedTotal = computed(() => {
  let t = 0
  for (const item of orderForm.value.items) {
    t += (Number(item.unit_price) || 0) * (Number(item.quantity) || 1)
  }
  return Math.round(t * 100) / 100
})

async function handleSubmit() {
  orderSaving.value = true
  try {
    const payload = {
      source: 'manual',
      buyer_nickname: orderForm.value.buyer_nickname || null,
      order_time: orderForm.value.order_time ? orderForm.value.order_time + ':00' : null,
      total_amount: computedTotal.value,
      discount: Math.max(0, computedTotal.value - (Number(orderForm.value.actual_amount) || 0)),
      actual_amount: Number(orderForm.value.actual_amount) || 0,
      shipping_fee: orderForm.value.shipping_fee != null ? Number(orderForm.value.shipping_fee) : null,
      packaging_fee: orderForm.value.packaging_fee != null ? Number(orderForm.value.packaging_fee) : null,
      service_fee: orderForm.value.service_fee != null ? Number(orderForm.value.service_fee) : null,
      service_fee_rate: orderForm.value.service_fee_rate != null ? Number(orderForm.value.service_fee_rate) / 100 : null,
      charity_fee: orderForm.value.charity_fee != null ? Number(orderForm.value.charity_fee) : null,
      charity_fee_rate: orderForm.value.charity_fee_rate != null ? Number(orderForm.value.charity_fee_rate) / 100 : null,
      notes: orderForm.value.notes || null,
      items: orderForm.value.items.map(item => ({
        product_id: Number(item.product_id),
        product_name: item.product_name,
        quantity: Number(item.quantity),
        unit_price: Number(item.unit_price),
        material_cost: Number(item.material_cost),
      })),
    }

    if (editingOrder.value) {
      await put(`/api/orders/${editingOrder.value.id}`, payload)
    } else {
      await post('/api/orders', payload)
    }
    modalVisible.value = false
    await fetchAll()
  } finally {
    orderSaving.value = false
  }
}

onMounted(fetchAll)
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">订单管理</h2>
        <p class="text-sm text-gold-muted mt-1">管理订单、粘贴导入、跟踪发货状态</p>
      </div>
      <div class="flex gap-2">
        <button
          class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
                 hover:bg-gold/30 transition-colors text-sm"
          @click="openCreate"
        >
          <Plus class="w-4 h-4" />
          新增订单
        </button>
        <router-link
          to="/paste-import"
          class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
                 hover:bg-gold/30 transition-colors text-sm"
        >
          <Search class="w-4 h-4" />
          粘贴导入
        </router-link>
        <button
          class="flex items-center gap-2 px-4 py-2 bg-dark-card border border-border-inner text-gray-400 rounded-lg
                 hover:text-gray-200 hover:bg-dark-input transition-colors text-sm"
          @click="exportCSV"
        >
          <Download class="w-4 h-4" />
          导出CSV
        </button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <select
        v-model="filters.status"
        class="px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      >
        <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <input
        v-model="filters.xianyu_order_id"
        type="text"
        placeholder="闲鱼订单号"
        class="w-40 px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50 placeholder-gray-600"
        @keyup.enter="applyFilters"
      />
      <select
        v-model="filters.product_id"
        class="px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      >
        <option value="">全部商品</option>
        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <input
        v-model="filters.date_from"
        type="date"
        class="w-36 px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      />
      <span class="text-gray-500 text-xs">至</span>
      <input
        v-model="filters.date_to"
        type="date"
        class="w-36 px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      />
      <button
        class="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 border border-border-inner rounded-md
               hover:bg-dark-card transition-colors"
        @click="clearFilters"
      >
        清除
      </button>
    </div>

    <!-- Order Table -->
    <DataTable
      :columns="columns"
      :data="orders"
      :loading="loading"
      :actions="orderActions"
      empty-text="暂无订单"
    >
      <template #cell-order_no="{ value }">
        <span class="text-sm text-gold font-mono">{{ value }}</span>
      </template>
      <template #cell-xianyu_order_id="{ value }">
        <span class="text-xs text-gray-400 font-mono">{{ value || '-' }}</span>
      </template>
      <template #cell-status="{ value }">
        <StatusBadge :status="value" />
      </template>
      <template #cell-buyer_nickname="{ value }">
        <span class="text-sm text-gray-200">{{ value || '-' }}</span>
      </template>
      <template #cell-total_amount="{ value }">
        <span class="text-sm text-gray-500 line-through">¥{{ Number(value).toFixed(2) }}</span>
      </template>
      <template #cell-actual_amount="{ value }">
        <span class="text-gold-price font-medium">¥{{ Number(value).toFixed(2) }}</span>
      </template>
      <template #cell-source="{ value }">
        <span class="text-xs px-2 py-0.5 rounded bg-dark-input text-gray-400">
          {{ { paste_import: '粘贴导入', manual: '手动', wechat: '微信', migrated: '旧版导入' }[value] || value }}
        </span>
      </template>
      <template #cell-order_time="{ value }">
        <span class="text-sm text-gray-400">{{ value ? value.slice(0, 10) : '-' }}</span>
      </template>
      <template #cell-completed_time="{ value }">
        <span class="text-sm text-gray-400">{{ value ? value.slice(0, 10) : '-' }}</span>
      </template>
    </DataTable>

    <!-- Pagination -->
    <div v-if="totalOrders > 0" class="flex items-center justify-between mt-4 text-sm text-gray-400">
      <div>共 {{ totalOrders }} 条订单</div>
      <div class="flex items-center gap-3">
        <button
          class="px-3 py-1.5 rounded border border-border-inner hover:bg-dark-card hover:text-gray-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="currentPage <= 1"
          @click="goPage(currentPage - 1)"
        >
          上一页
        </button>
        <span class="text-gray-200">{{ currentPage }} / {{ totalPages }}</span>
        <button
          class="px-3 py-1.5 rounded border border-border-inner hover:bg-dark-card hover:text-gray-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="currentPage >= totalPages"
          @click="goPage(currentPage + 1)"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- Order Form Modal -->
    <Teleport to="body">
      <div
        v-if="modalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click.self="modalVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">
              {{ editingOrder ? '编辑订单' : '新增订单' }}
            </h3>
            <button class="text-gray-500 hover:text-gray-300" @click="modalVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <!-- Row 1: Order Time + Buyer -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">下单时间</label>
                <input v-model="orderForm.order_time" type="datetime-local" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">买家昵称</label>
                <input v-model="orderForm.buyer_nickname" type="text" placeholder="可空" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
              </div>
            </div>

            <!-- Order Items -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm text-gray-400">订单明细</label>
                <button type="button" class="text-xs text-gold-muted hover:text-gold px-2 py-1 border border-border-inner rounded" @click="addOrderItem">
                  + 添加商品
                </button>
              </div>
              <div v-if="orderForm.items.length === 0" class="text-xs text-gray-500 py-3 text-center border border-dashed border-border-inner rounded-md">
                尚未添加商品
              </div>
              <div v-for="(item, idx) in orderForm.items" :key="idx" class="flex items-start gap-2 mb-2 p-3 bg-dark-input rounded-md border border-border-inner">
                <div class="flex-1">
                  <div class="grid grid-cols-5 gap-2">
                    <div class="col-span-2">
                      <label class="text-xs text-gray-500">商品</label>
                      <select v-model.number="item.product_id" class="w-full px-2 py-1.5 bg-dark-card border border-border-inner rounded text-sm text-gray-200 focus:outline-none focus:border-gold/50" @change="onItemProductChange(idx)">
                        <option :value="null" disabled>选择商品...</option>
                        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
                      </select>
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">数量</label>
                      <input v-model.number="item.quantity" type="number" min="1" class="w-full px-2 py-1.5 bg-dark-card border border-border-inner rounded text-sm text-gray-200 focus:outline-none focus:border-gold/50" @change="recalcTotal" />
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">单价</label>
                      <div class="w-full px-2 py-1.5 bg-dark-card/50 border border-border-inner rounded text-sm text-gray-400">
                        ¥{{ Number(item.unit_price).toFixed(2) }}
                      </div>
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">材料成本</label>
                      <div class="w-full px-2 py-1.5 bg-dark-card/50 border border-border-inner rounded text-sm text-gray-400">
                        ¥{{ Number(item.material_cost).toFixed(2) }}
                      </div>
                    </div>
                  </div>
                </div>
                <button type="button" class="shrink-0 mt-5 p-1 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded" @click="removeOrderItem(idx)"><X class="w-4 h-4" /></button>
              </div>
            </div>

            <!-- Amounts: read-only total + editable actual -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">原价总额（自动计算）</label>
                <div class="w-full px-3 py-2 bg-dark-input/50 border border-border-inner rounded-md text-gray-400 text-sm">
                  ¥{{ computedTotal.toFixed(2) }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">实付金额 <span class="text-red-400">*</span></label>
                <input v-model.number="orderForm.actual_amount" type="number" step="0.01" min="0" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
            </div>

            <!-- Fees -->
            <div class="grid grid-cols-4 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">运费</label>
                <input v-model.number="orderForm.shipping_fee" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">包装费</label>
                <input v-model.number="orderForm.packaging_fee" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">服务费</label>
                <input v-model.number="orderForm.service_fee" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">费率 %</label>
                <input v-model.number="orderForm.service_fee_rate" type="number" step="0.01" min="0" placeholder="1.6" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">公益支出</label>
                <input v-model.number="orderForm.charity_fee" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">公益费率 %</label>
                <input v-model.number="orderForm.charity_fee_rate" type="number" step="0.01" min="0" placeholder="1" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
              </div>
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">备注</label>
              <textarea v-model="orderForm.notes" rows="2" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" placeholder="可空"></textarea>
            </div>
          </form>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors" @click="modalVisible = false">取消</button>
            <button class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md hover:bg-gold/30 transition-colors disabled:opacity-50" :disabled="orderSaving" @click="handleSubmit">
              {{ orderSaving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
