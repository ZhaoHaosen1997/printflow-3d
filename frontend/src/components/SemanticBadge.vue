<script>
export const toneClasses = {
  success: 'bg-success/10 text-success border-success/30',
  danger: 'bg-danger/10 text-danger border-danger/30',
  warning: 'bg-warning/10 text-warning border-warning/30',
  info: 'bg-info/10 text-info border-info/30',
  accent: 'bg-gold/10 text-gold border-gold/30',
  neutral: 'bg-gray-400/10 text-gray-400 border-gray-400/30',
}
</script>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tone: { type: String, default: 'neutral' },
  label: { type: String, default: '' },
})

const toneClass = computed(() => toneClasses[props.tone] || toneClasses.neutral)
</script>

<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap border"
    :class="toneClass"
  >
    <slot>{{ label }}</slot>
  </span>
</template>
