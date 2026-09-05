<script setup>
import { ref, watch } from 'vue'
import { Copy } from '@lucide/vue'
import ModalShell from '../ModalShell.vue'
import { useApi } from '../../composables/useApi'
import { useToast } from '../../composables/useToast'

// 商品介绍生成/复制弹窗（原 Products.vue Description Modal）
const props = defineProps({
  modelValue: { type: Boolean, required: true },
  product: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])

const { get } = useApi()
const toast = useToast()

const text = ref('')
const loading = ref(false)
const copied = ref(false)

watch(() => props.modelValue, (open) => {
  if (open && props.product) {
    copied.value = false
    load()
  }
})

async function load() {
  loading.value = true
  copied.value = false
  try {
    const res = await get(`/api/descriptions/bundle/${props.product.id}`)
    text.value = res.text || ''
  } catch {
    // 失败已由 useApi 全局 toast 提示
  } finally {
    loading.value = false
  }
}

async function copy() {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text.value)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text.value
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    toast.error('复制失败，请手动复制')
  }
}

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <ModalShell
    v-if="modelValue"
    :title="`商品介绍 — ${product?.name || ''}`"
    width="max-w-2xl"
    @close="close"
  >
    <div class="flex-1 overflow-y-auto px-6 py-4">
      <textarea
        v-model="text"
        rows="20"
        spellcheck="false"
        class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm font-mono leading-relaxed
               focus:outline-none focus:border-gold/50 resize-y"
        placeholder="生成中..."
      ></textarea>
      <p class="text-xs text-gray-600 mt-2">可直接编辑后复制，修改保存到闲鱼即可</p>
    </div>
    <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
      <button
        class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
        @click="close"
      >
        关闭
      </button>
      <button
        class="px-4 py-2 text-sm text-gray-300 hover:text-gold border border-border-inner rounded-md hover:border-gold/40 transition-colors disabled:opacity-50"
        :disabled="loading"
        @click="load"
      >
        {{ loading ? '生成中...' : '重新生成' }}
      </button>
      <button
        class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md hover:bg-gold/30 transition-colors disabled:opacity-50"
        :disabled="loading"
        @click="copy"
      >
        <span class="flex items-center gap-1.5">
          <Copy class="w-3.5 h-3.5" />
          {{ copied ? '已复制' : '复制' }}
        </span>
      </button>
    </div>
  </ModalShell>
</template>
