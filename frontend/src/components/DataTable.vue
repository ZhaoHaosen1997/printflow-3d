<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  columns: { type: Array, required: true },
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无数据' },
  actions: { type: Array, default: () => [] },
})

const emit = defineEmits(['sort'])

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

function cellValue(row, col) {
  const val = row[col.key]
  if (col.format) return col.format(val, row)
  if (val == null) return '-'
  return val
}
</script>

<template>
  <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
    <table class="w-full">
      <thead>
        <tr class="border-b border-border-inner">
          <th
            v-for="col in columns"
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
          <th v-if="actions.length" class="px-4 py-3 text-right text-xs font-medium text-gold-muted uppercase tracking-wider w-24">
            操作
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-if="loading">
          <tr v-for="i in 5" :key="'skeleton-' + i" class="border-b border-border-inner/50">
            <td v-for="col in columns" :key="col.key" class="px-4 py-3">
              <div class="h-4 bg-dark-input rounded animate-pulse" :style="{ width: Math.random() * 60 + 40 + '%' }"></div>
            </td>
            <td v-if="actions.length" class="px-4 py-3"></td>
          </tr>
        </template>
        <template v-else-if="sortedData.length === 0">
          <tr>
            <td :colspan="columns.length + (actions.length ? 1 : 0)" class="px-4 py-12 text-center text-gray-500">
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
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-3 text-sm"
            >
              <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                {{ cellValue(row, col) }}
              </slot>
            </td>
            <td v-if="actions.length" class="px-4 py-3 text-right">
              <button
                v-for="action in actions"
                :key="action.label"
                v-show="!action.condition || action.condition(row)"
                class="ml-1 px-2 py-1 text-xs rounded transition-colors"
                :class="action.class || 'text-gold-muted hover:text-gold hover:bg-gold/10'"
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
</template>
