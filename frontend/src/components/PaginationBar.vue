<script setup>
// 分页条（配合 usePagination 使用），替代三处逐字重复的上一页/下一页按钮组
const props = defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  total: { type: Number, default: null },
  unit: { type: String, default: '条' },
})

const emit = defineEmits(['go'])
</script>

<template>
  <div class="flex items-center justify-between mt-4">
    <span v-if="total != null" class="text-xs text-gray-500">共 {{ total }} {{ unit }}</span>
    <span v-else></span>
    <div class="flex items-center gap-2">
      <button
        class="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 border border-border-inner rounded-md
               transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        :disabled="page <= 1"
        @click="emit('go', page - 1)"
      >
        上一页
      </button>
      <span class="text-xs text-gray-500">{{ page }} / {{ totalPages }}</span>
      <button
        class="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200 border border-border-inner rounded-md
               transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        :disabled="page >= totalPages"
        @click="emit('go', page + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>
