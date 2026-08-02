<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { TrendingUp, DollarSign, ShoppingCart, Users, Receipt } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import { useBreakpoint } from '../composables/useBreakpoint'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  Title, Tooltip, Legend, Filler,
  ArcElement, DoughnutController,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, Filler, ArcElement, DoughnutController)

const { get } = useApi()
const { isMobile } = useBreakpoint()

const year = ref(new Date().getFullYear())
const dateFrom = ref('')
const dateTo = ref('')
const productSort = ref('profit')

const overview = ref(null)
const monthly = ref([])
const products = ref([])
const loading = ref(false)
const cardHovered = ref(false)
const popoverHovered = ref(false)
const costPopoverOpen = ref(false)

const showCostPopover = computed(() => {
  if (isMobile.value) return costPopoverOpen.value
  return cardHovered.value || popoverHovered.value
})

function toggleCostPopover() {
  if (isMobile.value) costPopoverOpen.value = !costPopoverOpen.value
}

const totalCost = computed(() => {
  if (!overview.value) return 0
  return Number(overview.value.total_material_cost) +
    Number(overview.value.total_shipping_fee) +
    Number(overview.value.total_packaging_fee) +
    Number(overview.value.total_service_fee) +
    Number(overview.value.total_charity_fee)
})

const costPieData = computed(() => ({
  labels: ['材料成本', '运费', '包装费', '服务费', '公益支出'],
  datasets: [{
    data: overview.value ? [
      Number(overview.value.total_material_cost),
      Number(overview.value.total_shipping_fee),
      Number(overview.value.total_packaging_fee),
      Number(overview.value.total_service_fee),
      Number(overview.value.total_charity_fee),
    ] : [],
    backgroundColor: [
      'rgba(239,68,68,0.7)',
      'rgba(251,146,60,0.7)',
      'rgba(250,204,21,0.7)',
      'rgba(148,163,184,0.7)',
      'rgba(203,213,225,0.7)',
    ],
    borderColor: [
      'rgba(239,68,68,0.9)',
      'rgba(251,146,60,0.9)',
      'rgba(250,204,21,0.9)',
      'rgba(148,163,184,0.9)',
      'rgba(203,213,225,0.9)',
    ],
    borderWidth: 1,
  }],
}))

const costPieOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#9ca3af', padding: 12, font: { size: 10 }, usePointStyle: true },
    },
    tooltip: {
      backgroundColor: '#1f2937',
      titleColor: '#d4af37',
      bodyColor: '#e5e7eb',
      borderColor: '#374151',
      borderWidth: 1,
      callbacks: {
        label: (ctx) => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0)
          const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0
          return `${ctx.label}: ¥${Number(ctx.raw).toFixed(2)} (${pct}%)`
        },
      },
    },
  },
}

const monthLabels = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

async function fetchAll() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (dateFrom.value) params.set('date_from', dateFrom.value)
    if (dateTo.value) params.set('date_to', dateTo.value)

    const [ov, mo, bp] = await Promise.all([
      get(`/api/sales/overview?${params}`),
      get(`/api/sales/monthly?year=${year.value}`),
      get(`/api/sales/by-product?${params}&sort_by=${productSort.value}`),
    ])
    overview.value = ov
    monthly.value = mo
    products.value = bp
  } finally {
    loading.value = false
  }
}

async function fetchByProduct() {
  const params = new URLSearchParams()
  if (dateFrom.value) params.set('date_from', dateFrom.value)
  if (dateTo.value) params.set('date_to', dateTo.value)
  products.value = await get(`/api/sales/by-product?${params}&sort_by=${productSort.value}`)
}

const chartData = computed(() => ({
  labels: monthLabels,
  datasets: [
    {
      label: '销售额',
      data: monthly.value.map(m => Number(m.revenue)),
      backgroundColor: 'rgba(212, 175, 55, 0.25)',
      borderColor: 'rgba(212, 175, 55, 0.8)',
      borderWidth: 1,
      borderRadius: 4,
    },
    {
      label: '利润',
      data: monthly.value.map(m => Number(m.profit)),
      backgroundColor: 'rgba(34, 197, 94, 0.25)',
      borderColor: 'rgba(34, 197, 94, 0.8)',
      borderWidth: 1,
      borderRadius: 4,
    },
  ],
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#9ca3af', usePointStyle: true, padding: 20, font: { size: 11 } },
    },
    tooltip: {
      backgroundColor: '#1f2937',
      titleColor: '#d4af37',
      bodyColor: '#e5e7eb',
      borderColor: '#374151',
      borderWidth: 1,
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ¥${Number(ctx.raw).toFixed(2)}`,
      },
    },
  },
  scales: {
    x: { ticks: { color: '#6b7280', font: { size: 11 } }, grid: { display: false } },
    y: { ticks: { color: '#6b7280', callback: v => `¥${v}` }, grid: { color: 'rgba(107,114,128,0.1)' } },
  },
}))

function formatCurrency(val) {
  if (val == null) return '-'
  return `¥${Number(val).toFixed(2)}`
}

function categoryLabel(cat) {
  const map = { counter: '计数器', token: '指示物', other: '其他', bundle: '合集' }
  return map[cat] || cat
}

watch(year, fetchAll)
watch(productSort, fetchByProduct)

onMounted(fetchAll)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">销售统计</h2>
        <p class="text-sm text-gold-muted mt-1">基于交易成功订单实时计算</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Year selector -->
        <select
          v-model="year"
          class="px-3 py-1.5 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                 focus:outline-none focus:border-gold/50"
        >
          <option v-for="y in [2024,2025,2026,2027,2028]" :key="y" :value="y">{{ y }}年</option>
        </select>
      </div>
    </div>

    <!-- Date filter -->
    <div class="flex flex-wrap items-center gap-2 md:gap-3 mb-6">
      <input
        v-model="dateFrom"
        type="date"
        class="px-3 py-1.5 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
               focus:outline-none focus:border-gold/50"
      />
      <span class="text-gray-500 text-sm">至</span>
      <input
        v-model="dateTo"
        type="date"
        class="px-3 py-1.5 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
               focus:outline-none focus:border-gold/50"
      />
      <button
        class="px-4 py-1.5 text-sm bg-gold/20 text-gold border border-gold/30 rounded-md
               hover:bg-gold/30 transition-colors"
        @click="fetchAll"
      >筛选</button>
    </div>

    <!-- Overview Cards -->
    <div v-if="overview" class="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      <div class="bg-dark-card border border-border-inner rounded-lg p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <DollarSign class="w-3.5 h-3.5" />
          总销售额
        </div>
        <div class="text-xl font-bold text-gold">{{ formatCurrency(overview.total_revenue) }}</div>
        <div class="text-xs text-gray-600 mt-1">{{ overview.total_orders }} 笔订单</div>
      </div>
      <div class="bg-dark-card border border-border-inner rounded-lg p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <TrendingUp class="w-3.5 h-3.5" />
          总利润
        </div>
        <div class="text-xl font-bold text-success">{{ formatCurrency(overview.total_profit) }}</div>
        <div class="text-xs text-gray-600 mt-1">
          利润率 {{ overview.total_revenue > 0 ? ((overview.total_profit / overview.total_revenue) * 100).toFixed(1) : 0 }}%
        </div>
      </div>
      <div
        class="bg-dark-card border border-border-inner rounded-lg p-4 relative cursor-default overflow-visible"
        @mouseenter="cardHovered = true"
        @mouseleave="cardHovered = false"
        @click="toggleCostPopover"
      >
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <Receipt class="w-3.5 h-3.5" />
          总成本
        </div>
        <div class="text-xl font-bold text-danger">{{ formatCurrency(totalCost) }}</div>
        <div class="text-xs text-gray-600 mt-1">
          占比 {{ overview.total_revenue > 0 ? ((totalCost / overview.total_revenue) * 100).toFixed(1) : 0 }}%
        </div>
        <!-- Cost breakdown popover -->
        <Transition name="popover">
          <div
            v-if="showCostPopover"
            class="absolute left-1/2 -translate-x-1/2 top-full mt-2 z-30
                   bg-dark-card border border-border-main rounded-lg shadow-2xl p-4 w-64"
            @mouseenter="popoverHovered = true"
            @mouseleave="popoverHovered = false"
          >
            <div class="absolute left-1/2 -translate-x-1/2 bottom-full w-0 h-0
                        border-l-8 border-r-8 border-b-8
                        border-l-transparent border-r-transparent border-b-border-main"></div>
            <Doughnut :data="costPieData" :options="costPieOptions" />
          </div>
        </Transition>
      </div>
      <div class="bg-dark-card border border-border-inner rounded-lg p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <ShoppingCart class="w-3.5 h-3.5" />
          客单价
        </div>
        <div class="text-xl font-bold text-gold">{{ formatCurrency(overview.avg_order_value) }}</div>
        <div class="text-xs text-gray-600 mt-1">均利润 {{ formatCurrency(overview.avg_profit_per_order) }}</div>
      </div>
      <div class="bg-dark-card border border-border-inner rounded-lg p-4">
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <Users class="w-3.5 h-3.5" />
          累计砍价
        </div>
        <div class="text-xl font-bold text-warning">{{ formatCurrency(overview.total_discount) }}</div>
        <div class="text-xs text-gray-600 mt-1">
          服务费 {{ formatCurrency(overview.total_service_fee) }}
        </div>
      </div>
    </div>

    <!-- Monthly Chart -->
    <div class="bg-dark-card border border-border-inner rounded-lg p-4 md:p-6 mb-6">
      <h3 class="text-sm font-medium text-gray-300 mb-4">{{ year }}年 月度销售趋势</h3>
      <div class="h-56 md:h-72">
        <Bar v-if="monthly.length" :data="chartData" :options="chartOptions" />
        <div v-else class="flex items-center justify-center h-full text-gray-500 text-sm">
          暂无数据
        </div>
      </div>
    </div>

    <!-- Product Ranking -->
    <div class="bg-dark-card border border-border-inner rounded-lg">
      <div class="flex items-center justify-between px-4 md:px-6 py-4 border-b border-border-inner">
        <h3 class="text-sm font-medium text-gray-300">商品销售排行</h3>
        <select
          v-model="productSort"
          class="px-3 py-1.5 bg-dark-input border border-border-inner rounded-md text-gray-200 text-xs
                 focus:outline-none focus:border-gold/50"
        >
          <option value="profit">按利润</option>
          <option value="quantity">按销量</option>
          <option value="revenue">按销售额</option>
        </select>
      </div>
      <!-- Desktop table -->
      <div v-if="!isMobile" class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border-inner/50">
              <th class="px-4 py-3 text-left text-xs text-gold-muted">#</th>
              <th class="px-4 py-3 text-left text-xs text-gold-muted">商品</th>
              <th class="px-4 py-3 text-left text-xs text-gold-muted">分类</th>
              <th class="px-4 py-3 text-right text-xs text-gold-muted">销量</th>
              <th class="px-4 py-3 text-right text-xs text-gold-muted">销售额</th>
              <th class="px-4 py-3 text-right text-xs text-gold-muted">材料成本</th>
              <th class="px-4 py-3 text-right text-xs text-gold-muted">利润</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="px-4 py-12 text-center text-gray-500">加载中...</td>
            </tr>
            <tr v-else-if="products.length === 0">
              <td colspan="7" class="px-4 py-12 text-center text-gray-500">暂无销售数据</td>
            </tr>
            <tr
              v-for="(p, idx) in products"
              :key="p.product_id"
              class="border-b border-border-inner/30 hover:bg-dark-input/30 transition-colors"
            >
              <td class="px-4 py-3 text-gray-500">{{ idx + 1 }}</td>
              <td class="px-4 py-3 text-gray-200">{{ p.product_name }}</td>
              <td class="px-4 py-3 text-gray-400 text-xs">{{ categoryLabel(p.category) }}</td>
              <td class="px-4 py-3 text-right text-gray-200">{{ p.quantity }}</td>
              <td class="px-4 py-3 text-right text-gray-200">{{ formatCurrency(p.revenue) }}</td>
              <td class="px-4 py-3 text-right text-gray-400">{{ formatCurrency(p.material_cost) }}</td>
              <td class="px-4 py-3 text-right">
                <span :class="Number(p.profit) >= 0 ? 'text-success' : 'text-danger'">
                  {{ formatCurrency(p.profit) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Mobile card list -->
      <div v-else>
        <div v-if="loading" class="px-4 py-12 text-center text-gray-500 text-sm">加载中...</div>
        <div v-else-if="products.length === 0" class="px-4 py-12 text-center text-gray-500 text-sm">暂无销售数据</div>
        <div
          v-for="(p, idx) in products"
          :key="p.product_id"
          class="px-4 py-3 border-b border-border-inner/30"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-200">{{ p.product_name }}</span>
            <span class="text-sm font-medium" :class="Number(p.profit) >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(p.profit) }}
            </span>
          </div>
          <div class="flex gap-3 mt-1 text-xs text-gray-500">
            <span>{{ categoryLabel(p.category) }}</span>
            <span>销量 {{ p.quantity }}</span>
            <span>收入 {{ formatCurrency(p.revenue) }}</span>
            <span>成本 {{ formatCurrency(p.material_cost) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.popover-enter-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.popover-leave-active { transition: opacity 0.1s ease, transform 0.1s ease; }
.popover-enter-from { opacity: 0; transform: translate(-50%, 4px); }
.popover-leave-to { opacity: 0; transform: translate(-50%, 4px); }
</style>
