<script setup>
import { ref } from 'vue'
import { Sparkles, Save, Check, X, AlertTriangle } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import StatusBadge from '../components/StatusBadge.vue'

const { loading, post } = useApi()

const pasteText = ref('')
const parsedOrders = ref([])
const parseErrors = ref([])
const saving = ref(false)
const savedIds = ref(new Set())

// Sample placeholder text
const sampleText = `待发货
订单编号

5115911365178080546点击复制
添加备注

下单时间 2026-05-14 12:01:03


【诡镇奇谈 token合集】3D打印桌游 指示物 合集
待发货
¥
38.00
×1
¥
35.19
包邮

CowBy16
王星杰
18961338180
江苏省连云港市海州区新浦街道凌州西路20号新月园1期`

async function handleParse() {
  if (!pasteText.value.trim()) return
  parseErrors.value = []
  try {
    const result = await post('/api/orders/parse', { text: pasteText.value })
    parsedOrders.value = result.orders || []
    parseErrors.value = result.errors || []
    savedIds.value = new Set()
  } catch (e) {
    parseErrors.value = [e.message || '解析失败']
  }
}

async function saveOrder(index) {
  const po = parsedOrders.value[index]
  saving.value = true
  try {
    let items = []
    if (po.is_bundle && po.bundle_items && po.bundle_items.length > 0) {
      // Fixed bundle (e.g., Token合集包): single item pointing to the bundle product
      const materialCost = po.bundle_items.reduce((sum, bi) => sum + (Number(bi.material_cost) || 0), 0)
      items = [{
        product_id: po.matched_product_id,
        product_name: po.product_name,
        quantity: po.quantity || 1,
        unit_price: Number(po.total_amount || 0),
        material_cost: Math.round(materialCost * 100) / 100,
      }]
    } else if (po.matched_product_id) {
      items = [{
        product_id: po.matched_product_id,
        product_name: po.product_name,
        quantity: po.quantity || 1,
        unit_price: Number(po.total_amount || 0),
        material_cost: 0,
      }]
    }

    await post('/api/orders', {
      xianyu_order_id: po.xianyu_order_id,
      buyer_nickname: po.buyer_nickname,
      buyer_province: po.buyer_province || null,
      status: po.status || 'pending_ship',
      order_time: po.order_time || null,
      total_amount: Number(po.total_amount || 0),
      discount: Number(po.discount || 0),
      actual_amount: Number(po.actual_amount || 0),
      source: 'paste_import',
      items,
    })
    savedIds.value.add(index)
  } catch (e) {
    alert(`保存失败: ${e.message}`)
  } finally {
    saving.value = false
  }
}

async function saveAll() {
  for (let i = 0; i < parsedOrders.value.length; i++) {
    if (!savedIds.value.has(i)) {
      await saveOrder(i)
    }
  }
}

function clearAll() {
  pasteText.value = ''
  parsedOrders.value = []
  parseErrors.value = []
  savedIds.value = new Set()
}

const statusLabel = {
  pending_ship: '待发货',
  shipped: '已发货',
  completed: '交易成功',
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">粘贴导入</h2>
        <p class="text-sm text-gold-muted mt-1">从闲鱼鱼小铺复制订单文本，一键解析导入</p>
      </div>
      <div class="flex gap-2">
        <button
          class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
          @click="clearAll"
        >
          <X class="w-4 h-4" />
          清空
        </button>
        <button
          class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
          @click="pasteText = sampleText"
        >
          填入示例
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <!-- Left: Input Area -->
      <div>
        <label class="block text-sm text-gray-400 mb-2">
          粘贴订单文本
          <span class="text-gold-muted">（支持一次粘贴多个订单，空行分隔）</span>
        </label>
        <textarea
          v-model="pasteText"
          class="w-full h-96 px-4 py-3 bg-dark-input border border-border-inner rounded-lg text-gray-200 text-sm
                 focus:outline-none focus:border-gold/50 placeholder-gray-600 resize-none font-mono"
          placeholder="从闲鱼鱼小铺复制订单文本，粘贴到这里..."
        ></textarea>
        <button
          class="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gold/20 text-gold border border-gold/30 rounded-lg
                 hover:bg-gold/30 transition-colors text-sm disabled:opacity-50"
          :disabled="!pasteText.trim() || loading"
          @click="handleParse"
        >
          <Sparkles class="w-4 h-4" />
          {{ loading ? '解析中...' : '解析订单' }}
        </button>

        <!-- Errors -->
        <div v-if="parseErrors.length" class="mt-4 p-3 bg-red-400/10 border border-red-400/20 rounded-lg">
          <div v-for="(err, idx) in parseErrors" :key="idx" class="text-sm text-red-400 flex items-start gap-2">
            <AlertTriangle class="w-4 h-4 shrink-0 mt-0.5" />
            {{ err }}
          </div>
        </div>
      </div>

      <!-- Right: Parsed Results -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-medium text-gray-300">
            解析结果
            <span v-if="parsedOrders.length" class="text-gold-muted">（{{ parsedOrders.length }} 个订单）</span>
          </h3>
          <button
            v-if="parsedOrders.length > 0 && savedIds.size < parsedOrders.length"
            class="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gold/20 text-gold border border-gold/30 rounded-md
                   hover:bg-gold/30 transition-colors"
            :disabled="saving"
            @click="saveAll"
          >
            <Save class="w-3.5 h-3.5" />
            {{ saving ? '保存中...' : '全部保存' }}
          </button>
        </div>

        <div v-if="parsedOrders.length === 0" class="text-center text-gray-500 py-16">
          在左侧粘贴订单文本并点击「解析订单」
        </div>

        <div class="space-y-3 max-h-[36rem] overflow-y-auto pr-1">
          <div
            v-for="(order, idx) in parsedOrders"
            :key="idx"
            class="p-4 bg-dark-card border border-border-inner rounded-lg"
            :class="{ 'border-green-400/30 bg-green-400/5': savedIds.has(idx) }"
          >
            <!-- Order Header -->
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <span v-if="savedIds.has(idx)" class="text-green-400"><Check class="w-4 h-4" /></span>
                <span class="text-sm font-medium text-gold font-mono">{{ order.xianyu_order_id || '(无订单号)' }}</span>
                <StatusBadge :status="order.status" />
              </div>
              <span class="text-xs text-gray-500">
                {{ order.order_time ? order.order_time.slice(0, 16) : '' }}
              </span>
            </div>

            <!-- Product -->
            <div class="text-sm mb-2">
              <span class="text-gray-400">商品: </span>
              <span :class="order.matched ? 'text-gold' : 'text-red-400'">
                {{ order.product_name || '(未识别)' }}
              </span>
              <span v-if="order.matched && order.is_bundle" class="ml-2 text-xs px-1.5 py-0.5 rounded bg-purple-400/15 text-purple-400">合集</span>
              <span v-if="!order.matched && order.product_name" class="ml-2 text-xs px-1.5 py-0.5 rounded bg-red-400/15 text-red-400">未匹配</span>
            </div>

            <!-- Bundle children -->
            <div v-if="order.bundle_items && order.bundle_items.length" class="mb-2 ml-2 pl-3 border-l-2 border-purple-400/20">
              <div class="text-xs text-gray-500 mb-1">合集将展开为以下子商品:</div>
              <div v-for="bi in order.bundle_items" :key="bi.product_id" class="text-xs text-gray-400">
                - {{ bi.product_name }} ¥{{ Number(bi.unit_price).toFixed(2) }}
              </div>
            </div>

            <!-- Price Info -->
            <div class="flex items-center gap-4 text-sm mb-2">
              <span class="text-gray-500 line-through">¥{{ Number(order.total_amount).toFixed(2) }}</span>
              <span class="text-gray-300">×{{ order.quantity }}</span>
              <span class="text-gold-price font-medium">实付 ¥{{ Number(order.actual_amount).toFixed(2) }}</span>
              <span v-if="Number(order.total_amount) > Number(order.actual_amount)" class="text-xs text-red-400">
                砍¥{{ (Number(order.total_amount) - Number(order.actual_amount)).toFixed(2) }}
              </span>
              <span v-if="order.shipping_free" class="text-xs text-green-400">包邮</span>
            </div>

            <!-- Buyer Info -->
            <div class="text-xs text-gray-500">
              <span>买家: {{ order.buyer_nickname || '(未识别)' }}</span>
              <span v-if="order.buyer_province" class="ml-3">{{ order.buyer_province }}</span>
              <span v-if="order.buyer_name" class="ml-3">{{ order.buyer_name }}</span>
              <span v-if="order.buyer_phone" class="ml-3">{{ order.buyer_phone }}</span>
            </div>
            <div v-if="order.buyer_address" class="text-xs text-gray-600 mt-1 truncate">
              {{ order.buyer_address }}
            </div>

            <!-- Save Button -->
            <div v-if="!savedIds.has(idx)" class="mt-3 flex justify-end">
              <button
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gold/20 text-gold border border-gold/30 rounded-md
                       hover:bg-gold/30 transition-colors"
                :disabled="saving"
                @click="saveOrder(idx)"
              >
                <Save class="w-3.5 h-3.5" />
                保存此订单
              </button>
            </div>
            <div v-else class="mt-3 text-right text-xs text-green-400">
              已保存
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
