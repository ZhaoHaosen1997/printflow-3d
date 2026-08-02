<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Truck, AlertTriangle, TrendingUp, Printer, RefreshCw } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import StatusBadge from '../components/StatusBadge.vue'

const { get } = useApi()
const router = useRouter()

const data = ref(null)
const loading = ref(false)

async function fetchSummary() {
  loading.value = true
  try {
    data.value = await get('/api/dashboard/summary')
  } finally {
    loading.value = false
  }
}

function goTo(path) {
  router.push(path)
}

function formatCurrency(val) {
  if (val == null) return '¥0.00'
  return `¥${Number(val).toFixed(2)}`
}

function formatDate(dt) {
  if (!dt) return '-'
  const d = new Date(dt)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

onMounted(fetchSummary)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">仪表盘</h2>
        <p class="text-sm text-gold-muted mt-1">经营全貌一览</p>
      </div>
      <button
        class="p-2 rounded-md bg-dark-card border border-border-inner hover:bg-dark-input transition-colors"
        :disabled="loading"
        @click="fetchSummary"
      >
        <RefreshCw class="w-4 h-4 text-gray-400" :class="{ 'animate-spin': loading }" />
      </button>
    </div>

    <!-- 4 Stat Cards -->
    <div v-if="data" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div
        class="bg-dark-card border border-border-inner rounded-lg p-4 cursor-pointer hover:border-gold/40 transition-colors"
        @click="goTo('/orders?status=pending_ship')"
      >
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <Truck class="w-3.5 h-3.5" />
          待发货
        </div>
        <div class="text-2xl font-bold text-gold">{{ data.pending_ship_count }}</div>
        <div class="text-xs text-gray-600 mt-1">件待发货</div>
      </div>

      <div
        class="bg-dark-card border rounded-lg p-4 cursor-pointer hover:border-gold/40 transition-colors"
        :class="data.low_stock_count > 0 ? 'border-danger/40' : 'border-border-inner'"
        @click="goTo('/inventories')"
      >
        <div class="flex items-center gap-2 text-xs mb-2" :class="data.low_stock_count > 0 ? 'text-danger' : 'text-gray-500'">
          <AlertTriangle class="w-3.5 h-3.5" />
          库存预警
        </div>
        <div class="text-2xl font-bold" :class="data.low_stock_count > 0 ? 'text-danger' : 'text-gray-200'">
          {{ data.low_stock_count }}
        </div>
        <div class="text-xs text-gray-600 mt-1">种商品库存不足</div>
      </div>

      <div
        class="bg-dark-card border border-border-inner rounded-lg p-4 cursor-pointer hover:border-gold/40 transition-colors"
        @click="goTo('/sales')"
      >
        <div class="flex items-center gap-2 text-gray-500 text-xs mb-2">
          <TrendingUp class="w-3.5 h-3.5" />
          本月利润
        </div>
        <div class="text-2xl font-bold" :class="Number(data.monthly_profit) >= 0 ? 'text-success' : 'text-danger'">
          {{ formatCurrency(data.monthly_profit) }}
        </div>
        <div class="text-xs text-gray-600 mt-1 space-y-0.5">
          <div>收入 {{ formatCurrency(data.monthly_revenue) }}</div>
          <div>成本 {{ formatCurrency(data.monthly_cost) }}</div>
        </div>
      </div>

      <div
        class="bg-dark-card border border-info/30 rounded-lg p-4 cursor-pointer hover:border-info/50 transition-colors"
        @click="goTo('/print-tasks?status=printing')"
      >
        <div class="flex items-center gap-2 text-info text-xs mb-2">
          <Printer class="w-3.5 h-3.5" />
          打印中
        </div>
        <div class="text-2xl font-bold text-info">{{ data.printing_count }}</div>
        <div class="text-xs text-gray-600 mt-1">
          {{ data.pending_print_count }} 个待打印
        </div>
      </div>
    </div>

    <!-- Loading skeleton for cards -->
    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div v-for="i in 4" :key="i" class="bg-dark-card border border-border-inner rounded-lg p-4 animate-pulse">
        <div class="h-3 bg-dark-input rounded w-16 mb-3"></div>
        <div class="h-7 bg-dark-input rounded w-12 mb-2"></div>
        <div class="h-3 bg-dark-input rounded w-20"></div>
      </div>
    </div>

    <!-- Recent Orders -->
    <div v-if="data" class="bg-dark-card border border-border-inner rounded-lg mb-6">
      <div class="flex items-center justify-between px-4 md:px-6 py-4 border-b border-border-inner">
        <h3 class="text-sm font-medium text-gray-300">最近订单</h3>
        <button
          class="text-xs text-gold-muted hover:text-gold transition-colors"
          @click="goTo('/orders')"
        >查看全部</button>
      </div>
      <div v-if="data.recent_orders.length === 0" class="px-4 md:px-6 py-8 text-center text-gray-500 text-sm">
        暂无订单
      </div>
      <div v-else>
        <div
          v-for="o in data.recent_orders"
          :key="o.id"
          class="px-4 md:px-6 py-3 border-b border-border-inner/30 last:border-b-0
                 hover:bg-dark-input/30 transition-colors cursor-pointer"
          @click="goTo(`/orders?status=${o.status}`)"
        >
          <div class="flex items-center justify-between gap-2">
            <div class="text-sm text-gray-200 font-mono whitespace-nowrap">{{ o.order_no }}</div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <div class="text-sm text-gold">{{ formatCurrency(o.actual_amount) }}</div>
              <StatusBadge :status="o.status" size="sm" />
            </div>
          </div>
          <div class="flex items-center gap-2 mt-1 text-xs">
            <span class="text-gray-400">{{ o.buyer_nickname || '-' }}</span>
            <span class="text-gray-600">·</span>
            <span class="text-gray-500 truncate">{{ o.item_summary }}</span>
            <span class="text-gray-600 ml-auto flex-shrink-0">{{ formatDate(o.order_time) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Print Task Stats -->
    <div v-if="data" class="bg-dark-card border border-border-inner rounded-lg">
      <div class="flex items-center justify-between px-4 md:px-6 py-4 border-b border-border-inner">
        <h3 class="text-sm font-medium text-gray-300">打印任务概览</h3>
        <button
          class="text-xs text-gold-muted hover:text-gold transition-colors"
          @click="goTo('/print-tasks')"
        >查看全部</button>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 md:p-6">
        <div class="text-center">
          <div class="text-2xl font-bold text-warning">{{ data.print_task_stats.pending }}</div>
          <div class="text-xs text-gray-500 mt-1">待打印</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-info">{{ data.print_task_stats.printing }}</div>
          <div class="text-xs text-gray-500 mt-1">打印中</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-success">{{ data.print_task_stats.done }}</div>
          <div class="text-xs text-gray-500 mt-1">已完成</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold text-danger">{{ data.print_task_stats.failed }}</div>
          <div class="text-xs text-gray-500 mt-1">失败</div>
        </div>
      </div>
    </div>
  </div>
</template>
