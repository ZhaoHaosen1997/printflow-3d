<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { RefreshCw, Search, X, HardDrive } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import { toggleItem } from '../utils/array'

const { get } = useApi()

const entries = ref([])
const loading = ref(false)
const logInfo = ref(null)
const autoRefresh = ref(false)

const filter = ref({
  levels: [],
  categories: [],
  keyword: '',
  date: '',
})

const page = ref(1)
const pageSize = 100
const hasMore = ref(true)

const allLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
const allCategories = ['API', 'BUSINESS', 'PARSER', 'DB', 'ERROR']

const levelColors = {
  DEBUG: 'text-gray-400',
  INFO: 'text-gray-200',
  WARNING: 'text-warning',
  ERROR: 'text-danger',
}

const levelBg = {
  DEBUG: '',
  INFO: '',
  WARNING: 'bg-warning/10',
  ERROR: 'bg-danger/10',
}

function toggle(arr, val) {
  toggleItem(arr, val)
}

function has(arr, val) {
  return arr.includes(val)
}

function buildParams() {
  let params = `?page=${page.value}&page_size=${pageSize}`
  const f = filter.value
  if (f.levels.length) params += `&level=${f.levels.join(',')}`
  if (f.categories.length) params += `&category=${f.categories.join(',')}`
  if (f.keyword) params += `&keyword=${encodeURIComponent(f.keyword)}`
  if (f.date) params += `&date=${f.date}`
  return params
}

async function fetchLogs(reset = false, { silent = false } = {}) {
  if (reset) {
    page.value = 1
    entries.value = []
  }
  loading.value = true
  try {
    const data = await get('/api/logs' + buildParams(), { silent: silent })
    if (reset) {
      entries.value = data
    } else {
      entries.value = [...entries.value, ...data]
    }
    hasMore.value = data.length >= pageSize
  } finally {
    loading.value = false
  }
}

async function fetchInfo() {
  try {
    logInfo.value = await get('/api/logs/info', { silent: true })
  } catch {
    // log info is non-critical, ignore
  }
}

function clearFilters() {
  filter.value = { levels: [], categories: [], keyword: '', date: '' }
  fetchLogs(true)
}

function applyFilters() {
  fetchLogs(true)
}

function loadMore() {
  page.value++
  fetchLogs(false)
}

let timer = null
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    timer = setInterval(() => fetchLogs(true, { silent: true }), 5000)
  } else {
    clearInterval(timer)
  }
}

onMounted(() => {
  fetchLogs(true)
  fetchInfo()
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">运行日志</h2>
        <p class="text-sm text-gold-muted mt-1">
          查看系统运行日志
          <span v-if="logInfo" class="ml-2 text-xs text-gray-500">
            {{ logInfo.total_entries }} 条 · {{ logInfo.size_mb }} MB · {{ logInfo.backup_count }} 个归档
          </span>
        </p>
      </div>
      <div class="flex gap-2">
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border transition-colors"
          :class="autoRefresh ? 'bg-success/10 text-success border-success/30' : 'text-gray-500 border-border-inner hover:text-gray-300 hover:bg-dark-input'"
          @click="toggleAutoRefresh"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': autoRefresh }" />
          {{ autoRefresh ? '自动刷新中' : '自动刷新' }}
        </button>
        <button
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 border border-border-inner rounded-md hover:text-gray-300 hover:bg-dark-input transition-colors"
          @click="fetchLogs(true)"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          刷新
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <!-- Level filter -->
      <div class="flex gap-1">
        <button
          v-for="lv in allLevels" :key="lv"
          class="px-2 py-1 text-xs rounded border transition-colors"
          :class="has(filter.levels, lv)
            ? { DEBUG: 'border-border-main bg-dark-input text-gray-200', INFO: 'border-border-main bg-dark-input text-gray-200', WARNING: 'border-warning/40 bg-warning/10 text-warning', ERROR: 'border-danger/40 bg-danger/10 text-danger' }[lv]
            : 'border-border-inner text-gray-500 hover:text-gray-300 hover:bg-dark-input'"
          @click="toggle(filter.levels, lv); applyFilters()"
        >{{ lv }}</button>
      </div>
      <span class="text-gray-500">|</span>
      <!-- Category filter -->
      <div class="flex gap-1">
        <button
          v-for="cat in allCategories" :key="cat"
          class="px-2 py-1 text-xs rounded border transition-colors"
          :class="has(filter.categories, cat)
            ? 'border-info/40 bg-info/10 text-info'
            : 'border-border-inner text-gray-500 hover:text-gray-300 hover:bg-dark-input'"
          @click="toggle(filter.categories, cat); applyFilters()"
        >{{ cat }}</button>
      </div>
      <span class="text-gray-500">|</span>
      <input
        v-model="filter.keyword"
        type="text"
        placeholder="关键词搜索..."
        class="w-40 px-2 py-1 bg-dark-input border border-border-inner rounded text-xs text-gray-200 focus:outline-none focus:border-gold/50 placeholder-gray-500"
        @keyup.enter="applyFilters"
      />
      <input
        v-model="filter.date"
        type="date"
        class="w-32 px-2 py-1 bg-dark-input border border-border-inner rounded text-xs text-gray-200 focus:outline-none focus:border-gold/50"
        @change="applyFilters"
      />
      <button
        class="px-2 py-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        @click="clearFilters"
      ><X class="w-3 h-3" /></button>
    </div>

    <!-- Log List -->
    <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
      <div class="flex items-center px-4 py-2 border-b border-border-inner bg-dark-input text-gray-400 text-[11px] font-medium">
        <span class="w-[200px] shrink-0">时间</span>
        <span class="w-20 shrink-0">级别</span>
        <span class="w-24 shrink-0">分类</span>
        <span>消息</span>
      </div>

      <div v-if="loading && entries.length === 0" class="text-center text-gray-400 py-16">
        加载中...
      </div>

      <div v-else-if="entries.length === 0" class="text-center text-gray-400 py-16">
        暂无日志记录
      </div>

      <div v-else class="max-h-[calc(100vh-260px)] overflow-y-auto">
        <div
          v-for="(entry, idx) in entries"
          :key="idx"
          class="flex items-start px-4 py-0.5 border-b border-border-inner/60 hover:bg-dark-input/50 transition-colors"
          :class="levelBg[entry.level]"
        >
          <span class="w-[200px] shrink-0 text-gray-400">{{ entry.time }}</span>
          <span class="w-20 shrink-0 font-medium" :class="levelColors[entry.level]">{{ entry.level }}</span>
          <span class="w-24 shrink-0 text-gray-500">{{ entry.category }}</span>
          <span class="break-all" :class="levelColors[entry.level]">{{ entry.message }}</span>
        </div>
      </div>
    </div>

    <!-- Load more -->
    <div v-if="hasMore && entries.length > 0" class="text-center mt-4">
      <button
        class="px-4 py-2 text-sm text-gray-500 border border-border-inner rounded-md hover:text-gray-300 hover:bg-dark-input transition-colors"
        :disabled="loading"
        @click="loadMore"
      >
        {{ loading ? '加载中...' : '加载更多' }}
      </button>
    </div>
  </div>
</template>
