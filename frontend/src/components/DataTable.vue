<script setup>
import { ref, computed } from 'vue'
import { useBreakpoint } from '../composables/useBreakpoint'

const props = defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无数据' },
  actions: { type: Array, default: () => [] },
})

const emit = defineEmits(['sort'])

const { isMobile } = useBreakpoint()

const sortKey = ref('')
const sortDir = ref('asc')

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

const sortedData = computed(() => {
  if (!sortKey.value) return props.data
  return [...props.data].sort((a, b) => {
    const va = a[sortKey.value]
    const vb = b[sortKey.value]
    if (va == null) return 1
    if (vb == null) return -1
    const cmp = va < vb ? -1 : va > vb ? 1 : 0
    return sortDir.value === 'asc' ? cmp : -cmp
  })
})

const visibleColumns = computed(() =>
  props.columns.filter(col => !isMobile.value || !col.mobileHidden)
)

function cellValue(row, col) {
  const val = row[col.key]
  if (col.format) return col.format(val, row)
  if (val == null) return '-'
  return val
}
</script>

<template>
  <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
    <!-- Desktop: Table view -->
    <div v-if="!isMobile" class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="border-b border-border-inner">
            <th
              v-for="col in visibleColumns"
              :key="col.key"
              class="px-4 py-3 text-left text-xs font-medium text-gold-muted uppercase tracking-wider"
              :class="{ 'cursor-pointer hover:text-gold select-none': col.sortable }"
              :style="col.width ? { width: col.width } : {}"
              @click="col.sortable && toggleSort(col.key)"
            >
              {{ col.label }}
              <span v-if="sortKey === col.key" class="ml-1 text-gold">
                {{ sortDir === 'asc' ? '^' : 'v' }}
              </span>
            </th>
            <th v-if="actions.length" class="px-4 py-3 text-right text-xs font-medium text-gold-muted uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 5" :key="'skeleton-' + i" class="border-b border-border-inner/50">
              <td v-for="col in visibleColumns" :key="col.key" class="px-4 py-3">
                <div class="h-4 bg-dark-input rounded animate-pulse" :style="{ width: Math.random() * 60 + 40 + '%' }"></div>
              </td>
              <td v-if="actions.length" class="px-4 py-3"></td>
            </tr>
          </template>
          <template v-else-if="sortedData.length === 0">
            <tr>
              <td :colspan="visibleColumns.length + (actions.length ? 1 : 0)" class="px-4 py-12 text-center text-gray-500">
                {{ emptyText }}
              </td>
            </tr>
          </template>
          <template v-else>
            <tr
              v-for="(row, idx) in sortedData"
              :key="row.id || idx"
              class="border-b border-border-inner/30 hover:bg-dark-input/50 transition-colors"
            >
              <td
                v-for="col in visibleColumns"
                :key="col.key"
                class="px-4 py-3 text-sm"
              >
                <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                  {{ cellValue(row, col) }}
                </slot>
              </td>
              <td v-if="actions.length" class="px-4 py-3 text-right whitespace-nowrap">
                <button
                  v-for="action in actions"
                  :key="action.label"
                  v-show="!action.condition || action.condition(row)"
                  class="ml-1 px-2.5 py-1 text-xs rounded-md transition-colors inline-block border"
                  :class="action.class || 'btn-outline'"
                  @click="action.handler(row)"
                >
                  {{ action.label }}
                </button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Mobile: Card view -->
    <div v-else>
      <template v-if="loading">
        <div v-for="i in 3" :key="'skeleton-' + i" class="p-3 border-b border-border-inner/30">
          <div class="h-4 bg-dark-input rounded animate-pulse w-2/3 mb-2"></div>
          <div class="h-3 bg-dark-input rounded animate-pulse w-1/2"></div>
        </div>
      </template>
      <template v-else-if="sortedData.length === 0">
        <div class="px-4 py-12 text-center text-gray-500 text-sm">{{ emptyText }}</div>
      </template>
      <template v-else>
        <div
          v-for="(row, idx) in sortedData"
          :key="row.id || idx"
          class="p-3 border-b border-border-inner/30"
        >
          <div class="flex flex-wrap gap-x-4 gap-y-1">
            <template v-for="col in visibleColumns" :key="col.key">
              <div class="min-w-0">
                <span class="text-xs text-gray-500 mr-1">{{ col.mobileLabel || col.label }}:</span>
                <span class="text-sm text-gray-200">
                  <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                    {{ cellValue(row, col) }}
                  </slot>
                </span>
              </div>
            </template>
          </div>
          <div v-if="actions.length" class="flex gap-1 mt-2 pt-2 border-t border-border-inner/20">
            <button
              v-for="action in actions"
              :key="action.label"
              v-show="!action.condition || action.condition(row)"
              class="px-2.5 py-1 text-xs rounded-md transition-colors border min-h-[44px]"
              :class="action.class || 'btn-outline'"
              @click="action.handler(row)"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.btn-outline {
  color: var(--app-text-dim);
  border-color: var(--app-border-light);
  background: transparent;
}
.btn-outline:hover {
  color: var(--app-accent);
  border-color: var(--app-accent);
  background: color-mix(in srgb, var(--app-accent) 8%, transparent);
}

.btn-ghost {
  color: var(--app-text-dim);
  border-color: transparent;
  background: transparent;
}
.btn-ghost:hover {
  color: var(--app-accent);
  border-color: transparent;
  background: color-mix(in srgb, var(--app-accent) 10%, transparent);
}

.btn-soft {
  color: var(--app-accent);
  border-color: color-mix(in srgb, var(--app-accent) 30%, transparent);
  background: color-mix(in srgb, var(--app-accent) 10%, transparent);
}
.btn-soft:hover {
  color: var(--app-accent);
  border-color: var(--app-accent);
  background: color-mix(in srgb, var(--app-accent) 20%, transparent);
}

.btn-filled {
  color: #fff;
  border-color: var(--app-accent);
  background: var(--app-accent);
}
.btn-filled:hover {
  color: #fff;
  border-color: var(--app-accent-hover);
  background: var(--app-accent-hover);
}

.btn-danger-outline {
  color: var(--badge-danger-text);
  border-color: color-mix(in srgb, var(--badge-danger-text) 30%, transparent);
  background: transparent;
}
.btn-danger-outline:hover {
  color: #fff;
  border-color: var(--badge-danger-text);
  background: var(--badge-danger-text);
}
</style>
