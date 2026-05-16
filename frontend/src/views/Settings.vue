<script setup>
import { ref, onMounted } from 'vue'
import { Save } from '@lucide/vue'
import { useApi } from '../composables/useApi'

const { loading, get, put } = useApi()
const settings = ref([])
const saving = ref(false)
const saved = ref(false)

const labels = {
  shipping_fee: '默认运费 (元)',
  service_fee_rate: '服务费费率 (%)',
  packaging_fee: '单品包装费 (元)',
  packaging_fee_bundle: '合集包装费 (元)',
}

const hints = {
  shipping_fee: '卖家实际快递成本（利润计算时扣除）',
  service_fee_rate: '闲鱼平台服务费比例，如当前鱼小铺 1.6%',
  packaging_fee: '非合集订单的包装材料费',
  packaging_fee_bundle: '合集订单的包装材料费',
}

function isPercent(key) {
  return key === 'service_fee_rate'
}

async function fetchSettings() {
  const data = await get('/api/settings')
  settings.value = data.map(s => ({
    ...s,
    _editValue: isPercent(s.key) ? String(Number(s.value) * 100) : s.value,
  }))
}

async function saveSetting(item) {
  saving.value = true
  saved.value = false
  try {
    const storageValue = String(
      isPercent(item.key)
        ? Number(item._editValue) / 100
        : item._editValue
    )
    const updated = await put(`/api/settings/${item.key}`, { value: storageValue })
    item.value = updated.value
    item._editValue = isPercent(updated.key) ? String(Number(updated.value) * 100) : updated.value
    saved.value = true
    setTimeout(() => (saved.value = false), 2000)
  } finally {
    saving.value = false
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">全局配置</h2>
        <p class="text-sm text-gold-muted mt-1">新建订单时自动套用的默认值</p>
      </div>
      <div
        v-if="saved"
        class="text-sm text-green-400 flex items-center gap-1"
      >
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-green-400"></span>
        已保存
      </div>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 4" :key="i" class="bg-dark-card border border-border-inner rounded-lg p-6 animate-pulse">
        <div class="h-4 bg-dark-input rounded w-32 mb-3"></div>
        <div class="h-9 bg-dark-input rounded w-48"></div>
      </div>
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="item in settings"
        :key="item.key"
        class="bg-dark-card border border-border-inner rounded-lg p-6"
      >
        <div class="flex items-start justify-between gap-6">
          <div class="flex-1">
            <label class="block text-sm text-gray-200 font-medium mb-1">
              {{ labels[item.key] || item.key }}
            </label>
            <p class="text-xs text-gray-500 mb-3">{{ hints[item.key] || item.description }}</p>
            <div class="flex items-center gap-3">
              <input
                v-model="item._editValue"
                type="number"
                :step="isPercent(item.key) ? '0.01' : '0.01'"
                min="0"
                class="w-48 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50"
              />
              <button
                class="flex items-center gap-1.5 px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                       hover:bg-gold/30 transition-colors disabled:opacity-50"
                :disabled="saving"
                @click="saveSetting(item)"
              >
                <Save class="w-3.5 h-3.5" />
                保存
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
