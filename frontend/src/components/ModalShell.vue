<script setup>
import { X } from '@lucide/vue'

// 全站统一的 Modal 外壳：只负责遮罩/卡片/标题/关闭，内容交给插槽。
// 替代此前在 8 个页面手工复制的 Teleport + fixed + 头部 + 关闭按钮结构。
const props = defineProps({
  title: { type: String, default: '' },
  width: { type: String, default: 'max-w-lg' },
  // 嵌套弹窗（如配方表单叠在配方列表上）用 z-[60]
  z: { type: String, default: 'z-50' },
  // 点击遮罩是否关闭
  dismissable: { type: Boolean, default: true },
})

const emit = defineEmits(['close'])

function requestClose() {
  if (props.dismissable) emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      :class="z"
      @mousedown.self="requestClose"
    >
      <div
        class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full mx-4 max-h-[85vh] flex flex-col"
        :class="width"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
          <h3 class="text-lg font-serif text-gold-title">{{ title }}</h3>
          <button class="text-gray-500 hover:text-gray-300" aria-label="关闭" @click="requestClose">
            <X class="w-5 h-5" />
          </button>
        </div>
        <slot />
      </div>
    </div>
  </Teleport>
</template>
