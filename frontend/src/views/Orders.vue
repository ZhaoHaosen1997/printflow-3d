<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, X, Search, Download } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import { useToast } from '../composables/useToast'
import { ORDER_STATUS as orderStatusLabelMap, SOURCE_LABELS } from '../constants/orderStatus'
import PaginationBar from '../components/PaginationBar.vue'
import DataTable from '../components/DataTable.vue'
import ModalShell from '../components/ModalShell.vue'
import StatusBadge from '../components/StatusBadge.vue'

const { loading, get, post, put, del } = useApi()
const toast = useToast()
const route = useRoute()

const orders = ref([])
const totalOrders = ref(0)
const currentPage = ref(1)
const pageSize = ref(30)
const products = ref([])
const settings = ref({})
const stockMap = ref({})
const actualAuto = ref(true)

const statuses = [
  { value: '', label: '全部状态' },
  ...Object.entries(orderStatusLabelMap)
    .filter(([key]) => key !== 'archived')
    .map(([value, label]) => ({ value, label })),
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
  { key: 'order_no', label: '订单编号', sortable: true, mobileLabel: '编号' },
  { key: 'xianyu_order_id', label: '闲鱼订单号', mobileHidden: true },
  { key: 'status', label: '状态', mobileLabel: '状态' },
  { key: 'buyer_nickname', label: '买家', mobileLabel: '买家' },
  { key: 'total_amount', label: '原价', mobileHidden: true },
  { key: 'actual_amount', label: '实付', mobileLabel: '金额' },
  { key: 'source', label: '来源', mobileHidden: true },
  { key: 'order_time', label: '下单时间', sortable: true, mobileLabel: '时间' },
  { key: 'completed_time', label: '完成时间', mobileHidden: true },
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
  xianyu_order_id: '',
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

let fetchSeq = 0
async function fetchAll() {
  const seq = ++fetchSeq
  const offset = (currentPage.value - 1) * pageSize.value
  let params = `?limit=${pageSize.value}&offset=${offset}`
  const f = filters.value
  if (f.status) params += `&status=${encodeURIComponent(f.status)}`
  if (f.xianyu_order_id) params += `&xianyu_order_id=${encodeURIComponent(f.xianyu_order_id)}`
  if (f.product_id) params += `&product_id=${f.product_id}`
  if (f.date_from) params += `&date_from=${f.date_from}`
  if (f.date_to) params += `&date_to=${f.date_to}`
  const [ordData, prod, sett] = await Promise.all([
    get(`/api/orders${params}`),
    get('/api/products'),
    get('/api/settings'),
  ])
  // 快速翻页/切筛选时丢弃过期响应，防止慢请求晚到覆盖新数据
  if (seq !== fetchSeq) return
  orders.value = ordData.items
  totalOrders.value = ordData.total
  products.value = prod.filter(p => p.status === 'active')
  const sm = {}
  sett.forEach(s => { sm[s.key] = s.value })
  settings.value = sm
  // 库存映射：仅用于保存后的"无库存"提示，不拦截下单
  try {
    const invs = await get('/api/inventories')
    const im = {}
    invs.forEach(i => { im[i.product_id] = i.quantity })
    stockMap.value = im
  } catch { /* 库存提示属辅助信息，拉取失败不阻塞 */ }
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
  } catch {
    toast.error('CSV导出失败，请重试')
  }
}

function resetForm() {
  const s = settings.value
  const isBundle = orderForm.value.items.length > 1
  orderForm.value = {
    order_time: new Date().toISOString().slice(0, 16),
    xianyu_order_id: '',
    actual_amount: null,
    shipping_fee: s.shipping_fee != null ? Number(s.shipping_fee) : null,
    packaging_fee: isBundle ? (s.packaging_fee_bundle != null ? Number(s.packaging_fee_bundle) : null) : (s.packaging_fee != null ? Number(s.packaging_fee) : null),
    service_fee: null,
    service_fee_rate: s.service_fee_rate != null ? Number(s.service_fee_rate) * 100 : null,
    charity_fee: null,
    charity_fee_rate: null,
    notes: '',
    buyer_nickname: '',
    items: [],
  }
  actualAuto.value = true
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
      xianyu_order_id: full.xianyu_order_id || '',
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
  await fetchAll()
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
  recalcItemPrices()
}

function recalcItemPrices() {
  const validItems = orderForm.value.items.filter(i => i.product_id)
  const totalQty = validItems.reduce((sum, i) => sum + (Number(i.quantity) || 1), 0)
  const useBundle = validItems.length > 1 || totalQty > 1
  for (const item of orderForm.value.items) {
    if (!item.product_id) continue
    const prod = products.value.find(p => p.id === Number(item.product_id))
    if (prod) {
      // 固定合集（如 Token合集包）：内容固定、有整体一口价(price_single)，
      // 无论单卖还是与其他商品同单，永远按 price_single 计价——
      // 不能被下方"多商品 → 用 price_bundle"的启发式覆盖(固定合集 price_bundle 为0)。
      if (prod.category === 'bundle') {
        item.unit_price = Number(prod.price_single) || 0
      } else {
        // 普通子商品：合集场景用 price_bundle 优惠价，price_bundle 无意义(0/空)时回退 price_single
        item.unit_price = useBundle
          ? Number(prod.price_bundle) || Number(prod.price_single) || 0
          : Number(prod.price_single) || 0
      }
      item.material_cost = Number(prod.material_cost) || 0
    }
  }
  recalcTotal()
}

function onItemProductChange(idx) {
  const item = orderForm.value.items[idx]
  const prod = products.value.find(p => p.id === Number(item.product_id))
  if (prod) {
    item.product_name = prod.name
    if (prod.charity_rate != null && orderForm.value.charity_fee_rate == null) {
      orderForm.value.charity_fee_rate = Number(prod.charity_rate) * 100
    }
    recalcItemPrices()
  }
}

function recalcTotal() {
  let total = 0
  for (const item of orderForm.value.items) {
    total += (Number(item.unit_price) || 0) * (Number(item.quantity) || 1)
  }
  if (actualAuto.value) {
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

const hasCharityProduct = computed(() => {
  return orderForm.value.items.some(item => {
    if (!item.product_id) return false
    const prod = products.value.find(p => p.id === Number(item.product_id))
    return prod && prod.charity_rate != null
  })
})

async function handleSubmit() {
  orderSaving.value = true
  try {
    const payload = {
      source: 'manual',
      xianyu_order_id: orderForm.value.xianyu_order_id || null,
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
    // 库存不足不拦截下单，仅在保存后提示（订单已按无库存记录）
    if (!editingOrder.value) {
      const need = {}
      payload.items.forEach(it => {
        need[it.product_id] = (need[it.product_id] || 0) + (it.quantity || 1)
      })
      const shortages = Object.entries(need)
        .filter(([pid, qty]) => (stockMap.value[pid] ?? 0) < qty)
        .map(([pid, qty]) => {
          const name = payload.items.find(it => it.product_id === Number(pid))?.product_name || `商品#${pid}`
          return `「${name}」库存 ${stockMap.value[pid] ?? 0}，需 ${qty}`
        })
      if (shortages.length) {
        toast.warning(`库存不足：${shortages.join('；')}，订单已保存，请尽快补货打印`)
      }
    }
    modalVisible.value = false
    await fetchAll()
  } finally {
    orderSaving.value = false
  }
}

onMounted(() => {
  // 支持 Dashboard 等外部入口携带 ?status=pending_ship 直达筛选
  for (const key of Object.keys(filters.value)) {
    const v = route.query[key]
    if (v != null && v !== '') filters.value[key] = v
  }
  fetchAll()
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">订单管理</h2>
        <p class="text-sm text-gold-muted mt-1">管理订单、粘贴导入、跟踪发货状态</p>
      </div>
      <div class="flex flex-wrap gap-2">
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
    <div class="grid grid-cols-2 sm:flex sm:flex-wrap items-center gap-2 mb-4">
      <select
        v-model="filters.status"
        class="w-full sm:w-auto px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      >
        <option v-for="s in statuses" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
      <input
        v-model="filters.xianyu_order_id"
        type="text"
        placeholder="闲鱼订单号"
        class="w-full sm:w-40 px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
                focus:outline-none focus:border-gold/50 placeholder-gray-600"
        @keyup.enter="applyFilters"
      />
      <select
        v-model="filters.product_id"
        class="w-full sm:w-auto px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
               focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      >
        <option value="">全部商品</option>
        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <div class="contents sm:contents">
        <input
          v-model="filters.date_from"
          type="date"
          class="w-full sm:w-36 px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
                 focus:outline-none focus:border-gold/50"
          @change="applyFilters"
        />
        <span class="hidden sm:inline text-gray-500 text-xs">至</span>
        <input
          v-model="filters.date_to"
          type="date"
          class="w-full sm:w-36 px-3 py-1.5 bg-dark-card border border-border-inner rounded-md text-sm text-gray-200
                 focus:outline-none focus:border-gold/50"
          @change="applyFilters"
        />
      </div>
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
          {{ SOURCE_LABELS[value] || value }}
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
    <PaginationBar
      v-if="totalOrders > 0"
      :page="currentPage"
      :total-pages="totalPages"
      :total="totalOrders"
      unit="条订单"
      @go="goPage"
    />

    <!-- Order Form Modal -->
    <ModalShell
      v-if="modalVisible"
      :title="editingOrder ? '编辑订单' : '新增订单'"
      width="max-w-3xl"
      @close="modalVisible = false"
    >

          <form @submit.prevent="handleSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <!-- Row 1: Order Time + Buyer + Xianyu ID -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">下单时间</label>
                <input v-model="orderForm.order_time" type="datetime-local" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">买家昵称</label>
                <input v-model="orderForm.buyer_nickname" type="text" placeholder="可空" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">闲鱼订单号</label>
                <input v-model="orderForm.xianyu_order_id" type="text" placeholder="可空" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
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
                  <div class="grid grid-cols-1 sm:grid-cols-5 gap-2">
                    <div class="col-span-2">
                      <label class="text-xs text-gray-500">商品</label>
                      <select v-model.number="item.product_id" class="w-full px-2 py-1.5 bg-dark-card border border-border-inner rounded text-sm text-gray-200 focus:outline-none focus:border-gold/50" @change="onItemProductChange(idx)">
                        <option :value="null" disabled>选择商品...</option>
                        <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
                      </select>
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">数量</label>
                      <input v-model.number="item.quantity" type="number" min="1" class="w-full px-2 py-1.5 bg-dark-card border border-border-inner rounded text-sm text-gray-200 focus:outline-none focus:border-gold/50" @change="recalcItemPrices" />
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">单价</label>
                      <div class="w-full px-2 py-1.5 bg-dark-input/30 border border-border-inner/50 rounded text-sm text-gray-500 cursor-default">
                        ¥{{ Number(item.unit_price).toFixed(2) }}
                      </div>
                    </div>
                    <div>
                      <label class="text-xs text-gray-500">材料成本</label>
                      <div class="w-full px-2 py-1.5 bg-dark-input/30 border border-border-inner/50 rounded text-sm text-gray-500 cursor-default">
                        ¥{{ Number(item.material_cost).toFixed(2) }}
                      </div>
                    </div>
                  </div>
                </div>
                <button type="button" class="shrink-0 mt-5 p-1 text-danger hover:text-danger hover:bg-danger/10 rounded" @click="removeOrderItem(idx)"><X class="w-4 h-4" /></button>
              </div>
            </div>

            <!-- Amounts: read-only total + editable actual -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">原价总额（自动计算）</label>
                <div class="w-full px-3 py-2 bg-dark-input/30 border border-border-inner/50 rounded-md text-gray-500 text-sm cursor-default">
                  ¥{{ computedTotal.toFixed(2) }}
                </div>
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">实付金额 <span class="text-danger">*</span></label>
                <input v-model.number="orderForm.actual_amount" type="number" step="0.01" min="0" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" @input="actualAuto = false" />
              </div>
            </div>

            <!-- Fees -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
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
              <div v-if="hasCharityProduct">
                <label class="block text-sm text-gray-400 mb-1">公益支出</label>
                <input v-model.number="orderForm.charity_fee" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div v-if="hasCharityProduct">
                <label class="block text-sm text-gray-400 mb-1">公益费率 %</label>
                <input v-model.number="orderForm.charity_fee_rate" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
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
    </ModalShell>
  </div>
</template>
