<script setup>
import { X, CheckCircle2, AlertCircle, Info } from '@lucide/vue'
import { useToast } from '../composables/useToast'

const { toasts, dismiss } = useToast()

const icons = { success: CheckCircle2, error: AlertCircle, info: Info }

const toneStyles = {
  success: 'border-success/30 text-success',
  error: 'border-danger/30 text-danger',
  info: 'border-info/30 text-info',
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 left-4 sm:left-auto z-[100] flex flex-col items-end gap-2 pointer-events-none"
      role="status" aria-live="polite"
    >
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-x-4"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto w-full sm:w-96 flex items-start gap-3 px-4 py-3
                 rounded-lg border bg-dark-card shadow-2xl"
          :class="toneStyles[t.type]"
        >
          <component :is="icons[t.type]" class="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p class="flex-1 text-sm text-gray-200 break-all">{{ t.message }}</p>
          <button
            class="flex-shrink-0 text-gray-500 hover:text-gray-300 transition-colors"
            aria-label="关闭提示"
            @click="dismiss(t.id)"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
