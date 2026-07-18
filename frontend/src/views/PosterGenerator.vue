<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { Image, Download, RefreshCw } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import { useBreakpoint } from '../composables/useBreakpoint'

const { get } = useApi()
const { isMobile } = useBreakpoint()

const posterType = ref('category')
const category = ref('counter')
const bundleId = ref(null)
const template = ref('parchment')
const width = ref(750)
const previewHtml = ref('')
const previewLoading = ref(false)
const downloading = ref(false)
const bundles = ref([])
const previewContainer = ref(null)
const iframeScale = ref(1)

const categoryOptions = [
  { value: 'counter', label: '计数器' },
  { value: 'token', label: '指示物' },
  { value: 'other', label: '其他配件' },
]

const templateOptions = [
  { value: 'parchment', label: '羊皮纸' },
  { value: 'dark-gold', label: '深色暗金' },
]

const widthOptions = [
  { value: 750, label: '750px' },
  { value: 1080, label: '1080px' },
]

const previewUrl = computed(() => {
  if (posterType.value === 'category') {
    return `/api/posters/category?category=${category.value}&template=${template.value}&width=${width.value}&preview=true`
  } else {
    if (!bundleId.value) return ''
    return `/api/posters/bundle/${bundleId.value}?template=${template.value}&width=${width.value}&preview=true`
  }
})

const downloadUrl = computed(() => {
  if (posterType.value === 'category') {
    return `/api/posters/category?category=${category.value}&template=${template.value}&width=${width.value}`
  } else {
    if (!bundleId.value) return ''
    return `/api/posters/bundle/${bundleId.value}?template=${template.value}&width=${width.value}`
  }
})

async function fetchBundles() {
  try {
    bundles.value = await get('/api/posters/bundles')
    if (bundles.value.length > 0 && !bundleId.value) {
      bundleId.value = bundles.value[0].id
    }
  } catch (e) {
    bundles.value = []
  }
}

function calcScale() {
  if (!previewContainer.value) return
  const containerWidth = previewContainer.value.clientWidth - 32
  const posterWidth = width.value
  iframeScale.value = Math.min(1, containerWidth / posterWidth)
}

function loadPreview() {
  if (!previewUrl.value) {
    previewHtml.value = ''
    return
  }
  previewLoading.value = true
  fetch(previewUrl.value)
    .then(res => res.text())
    .then(html => {
      previewHtml.value = html
      nextTick(() => calcScale())
    })
    .catch(() => {
      previewHtml.value = '<p style="text-align:center;color:#999;padding:40px;">Preview failed to load</p>'
    })
    .finally(() => {
      previewLoading.value = false
    })
}

function downloadPoster() {
  if (!downloadUrl.value) return
  downloading.value = true
  const link = document.createElement('a')
  link.href = downloadUrl.value
  link.download = ''
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => { downloading.value = false }, 2000)
}

watch([posterType, category, bundleId, template, width], () => {
  loadPreview()
})

onMounted(() => {
  fetchBundles()
  loadPreview()
  window.addEventListener('resize', calcScale)
})

import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => {
  window.removeEventListener('resize', calcScale)
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">长图生成</h2>
        <p class="text-sm text-gold-muted mt-1">生成商品合集长图，上传至闲鱼商品详情页</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
      <div class="space-y-4">
        <div class="bg-dark-card border border-border-inner rounded-lg p-5 space-y-5">
          <div>
            <label class="block text-sm text-gray-200 font-medium mb-2">生成类型</label>
            <div class="flex gap-3">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="posterType" value="category" class="accent-gold" />
                <span class="text-sm text-gray-300">分类合集</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="radio" v-model="posterType" value="bundle" class="accent-gold" />
                <span class="text-sm text-gray-300">固定合集</span>
              </label>
            </div>
          </div>

          <div v-if="posterType === 'category'">
            <label class="block text-sm text-gray-200 font-medium mb-2">分类</label>
            <select
              v-model="category"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            >
              <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div v-if="posterType === 'bundle'">
            <label class="block text-sm text-gray-200 font-medium mb-2">合集商品</label>
            <select
              v-model="bundleId"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            >
              <option v-for="b in bundles" :key="b.id" :value="b.id">
                {{ b.name }}（¥{{ b.price }}）
              </option>
            </select>
            <p v-if="bundles.length === 0" class="text-xs text-gray-500 mt-1">暂无合集商品</p>
          </div>

          <div>
            <label class="block text-sm text-gray-200 font-medium mb-2">模板风格</label>
            <select
              v-model="template"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            >
              <option v-for="opt in templateOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm text-gray-200 font-medium mb-2">图片宽度</label>
            <select
              v-model="width"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            >
              <option v-for="opt in widthOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>

        <button
          class="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm bg-gold/20 text-gold border border-gold/40 rounded-lg
                 hover:bg-gold/30 transition-colors disabled:opacity-50"
          :disabled="downloading || (posterType === 'bundle' && !bundleId)"
          @click="downloadPoster"
        >
          <Download class="w-4 h-4" />
          {{ downloading ? '生成中...' : '生成并下载' }}
        </button>

        <button
          class="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-gray-400 border border-border-inner rounded-lg
                 hover:text-gray-200 hover:bg-dark-input transition-colors"
          @click="loadPreview"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          刷新预览
        </button>
      </div>

      <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
        <div class="px-4 py-3 border-b border-border-inner flex items-center gap-2">
          <Image class="w-4 h-4 text-gold" />
          <span class="text-sm text-gray-300">预览</span>
          <span class="text-xs text-gray-500 ml-2">{{ width }}px</span>
          <span v-if="previewLoading" class="text-xs text-gray-500 ml-2">加载中...</span>
        </div>
        <div ref="previewContainer" class="p-4 flex justify-center bg-dark-input/50 min-h-[300px] md:min-h-[400px] overflow-auto">
          <div
            v-if="previewHtml && isMobile"
            class="w-full"
          >
            <iframe
              :srcdoc="previewHtml"
              class="w-full"
              :style="{ minHeight: '400px', border: 'none' }"
            ></iframe>
          </div>
          <div
            v-else-if="previewHtml"
            :style="{
              width: width + 'px',
              transform: `scale(${iframeScale})`,
              transformOrigin: 'top center',
            }"
          >
            <iframe
              :srcdoc="previewHtml"
              :style="{
                width: width + 'px',
                minHeight: '600px',
                border: 'none',
              }"
            ></iframe>
          </div>
          <div v-else class="flex items-center justify-center text-gray-500 text-sm">
            {{ posterType === 'bundle' && !bundleId ? '请选择合集商品' : '选择参数后自动加载预览' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
