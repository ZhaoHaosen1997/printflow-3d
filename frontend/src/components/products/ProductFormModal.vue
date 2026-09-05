<script setup>
import { ref, computed, watch } from 'vue'
import { X, Upload } from '@lucide/vue'
import ModalShell from '../ModalShell.vue'
import ImageCropModal from './ImageCropModal.vue'
import { useApi } from '../../composables/useApi'
import { toggleItem } from '../../utils/array'

// 商品表单弹窗（原 Products.vue Product Form Modal，含配色选择器）
// 用法：
//   <ProductFormModal v-model="open" :product="editing" :categories :games :colors :bundle-candidates @saved="onSaved" />
const props = defineProps({
  modelValue: { type: Boolean, required: true },
  product: { type: Object, default: null }, // null = 新增
  categories: { type: Array, default: () => [] },
  games: { type: Array, default: () => [] },
  colors: { type: Array, default: () => [] },
  bundleCandidates: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { get, post, put } = useApi()

const saving = ref(false)

const form = ref({})
const colorMode = ref('fixed') // 'fixed' | 'optional'
const selectedFixedColorId = ref(null)
const selectedOptionalColorIds = ref([])

// 图片裁剪
const cropModalVisible = ref(false)
const cropSrc = ref('')
const cropFilename = ref('')

const activeCategories = computed(() => props.categories.filter(c => c.status === 'active'))
const activeGames = computed(() => props.games.filter(g => g.status === 'active'))

watch(() => props.modelValue, (open) => {
  if (open) initForm()
})

function initForm() {
  const row = props.product
  if (!row) {
    form.value = {
      name: '',
      category_id: props.categories.length > 0 ? props.categories.find(c => c.status === 'active')?.id ?? null : null,
      xianyu_item_id: '',
      price_single: 0,
      price_bundle: 0,
      image: '',
      bundle_items: [],
      contents: [],
      charity_rate: '',
      search_keywords: '',
      game_ids: props.games.length > 0 && props.games.some(g => g.status === 'active')
        ? [props.games.find(g => g.status === 'active').id]
        : [],
    }
    colorMode.value = 'fixed'
    selectedFixedColorId.value = null
    selectedOptionalColorIds.value = []
    return
  }
  form.value = {
    name: row.name,
    category_id: row.category_id,
    xianyu_item_id: row.xianyu_item_id || '',
    price_single: row.price_single,
    price_bundle: row.price_bundle,
    image: row.image || '',
    bundle_items: row.bundle_items ? [...row.bundle_items] : [],
    contents: row.contents ? [...row.contents] : [],
    charity_rate: row.charity_rate != null ? String(row.charity_rate) : '',
    search_keywords: row.search_keywords ? row.search_keywords.join(', ') : '',
    game_ids: row.games ? row.games.map(g => g.id) : [],
  }
  const c = row.colors
  if (c && c.type === '固定') {
    colorMode.value = 'fixed'
    selectedFixedColorId.value = c.colorSetId || null
    selectedOptionalColorIds.value = []
  } else if (c && c.type === '可选') {
    colorMode.value = 'optional'
    selectedFixedColorId.value = null
    selectedOptionalColorIds.value = c.optionalColorSetIds ? [...c.optionalColorSetIds] : []
  } else {
    colorMode.value = 'fixed'
    selectedFixedColorId.value = null
    selectedOptionalColorIds.value = []
  }
}

function isBundleCategory() {
  const cat = props.categories.find(c => c.id === form.value.category_id)
  return cat && cat.slug === 'bundle'
}

function toggleGameId(gameId) {
  toggleItem(form.value.game_ids, gameId)
}

function selectFixedColor(colorId) {
  selectedFixedColorId.value = colorId
}

function toggleOptionalColor(colorId) {
  toggleItem(selectedOptionalColorIds.value, colorId)
}

function optionalColorSelected(colorId) {
  return selectedOptionalColorIds.value.includes(colorId)
}

function buildColorsPayload() {
  if (colorMode.value === 'fixed' && selectedFixedColorId.value) {
    const cs = props.colors.find(c => c.color_id === selectedFixedColorId.value)
    return {
      type: '固定',
      colorSetId: selectedFixedColorId.value,
      swatches: cs ? cs.swatches : [],
      label: cs ? cs.name : selectedFixedColorId.value,
    }
  }
  if (colorMode.value === 'optional' && selectedOptionalColorIds.value.length > 0) {
    const swatches = selectedOptionalColorIds.value.flatMap(id => {
      const cs = props.colors.find(c => c.color_id === id)
      return cs ? cs.swatches : []
    })
    const defaultId = selectedOptionalColorIds.value[0]
    const defaultCs = props.colors.find(c => c.color_id === defaultId)
    return {
      type: '可选',
      optionalColorSetIds: [...selectedOptionalColorIds.value],
      defaultColorSetId: defaultId,
      swatches,
      label: `可选配色（默认${defaultCs ? defaultCs.name : defaultId}）`,
    }
  }
  return null
}

function onImageUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    cropSrc.value = e.target.result
    cropFilename.value = file.name
    cropModalVisible.value = true
  }
  reader.readAsDataURL(file)
  event.target.value = ''
}

function removeImage() {
  form.value.image = ''
}

async function handleSubmit() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      charity_rate: form.value.charity_rate ? Number(form.value.charity_rate) : null,
      bundle_items: isBundleCategory() ? form.value.bundle_items : [],
      colors: buildColorsPayload(),
      search_keywords: form.value.search_keywords
        ? form.value.search_keywords.split(/[,，]/).map(s => s.trim()).filter(Boolean)
        : null,
    }
    const selectedCat = props.categories.find(c => c.id === form.value.category_id)
    if (selectedCat) payload.category = selectedCat.slug
    if (payload.xianyu_item_id === '') payload.xianyu_item_id = null

    let saved
    if (props.product) {
      saved = await put(`/api/products/${props.product.id}`, payload)
    } else {
      saved = await post('/api/products', payload)
    }
    emit('saved', saved)
    emit('update:modelValue', false)
  } catch {
    // 失败已由 useApi 全局 toast 提示
  } finally {
    saving.value = false
  }
}

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <ModalShell
    v-if="modelValue"
    :title="product ? '编辑商品' : '新增商品'"
    width="max-w-xl"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">名称 <span class="text-danger">*</span></label>
          <input v-model="form.name" type="text" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">分类 <span class="text-danger">*</span></label>
          <select v-model="form.category_id" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50">
            <option v-for="cat in activeCategories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">所属游戏</label>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="game in activeGames"
              :key="game.id"
              class="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-sm border cursor-pointer transition-colors"
              :class="form.game_ids.includes(game.id) ? 'bg-gold/20 text-gold border-gold/30' : 'text-gray-400 border-border-inner hover:border-gold/30'"
            >
              <input
                type="checkbox"
                :value="game.id"
                :checked="form.game_ids.includes(game.id)"
                @change="toggleGameId(game.id)"
                class="sr-only"
              />
              {{ game.name }}
            </label>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">单品售价 <span class="text-danger">*</span></label>
          <input v-model.number="form.price_single" type="number" step="0.01" min="0" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
          <p class="text-xs text-gray-600 mt-1">设为 0 表示不单卖（仅作为合集子商品）</p>
        </div>
        <div v-if="!isBundleCategory()">
          <label class="block text-sm text-gray-400 mb-1">合集优惠价</label>
          <input v-model.number="form.price_bundle" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
        </div>
      </div>

      <div>
        <label class="block text-sm text-gray-400 mb-1">公益宝贝费率</label>
        <select v-model="form.charity_rate" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50">
          <option value="">非公益宝贝</option>
          <option value="0.01">1%</option>
          <option value="0.50">50%</option>
          <option value="1.00">100%</option>
        </select>
      </div>

      <div>
        <label class="block text-sm text-gray-400 mb-1">闲鱼商品ID</label>
        <input v-model="form.xianyu_item_id" type="text" placeholder="未上架可留空" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
      </div>

      <div>
        <label class="block text-sm text-gray-400 mb-1">商品图片</label>
        <div v-if="form.image" class="relative group">
          <img :src="'/images/' + form.image" class="w-24 h-24 rounded-md object-cover border border-border-inner" @error="$event.target.style.display='none'" />
          <div class="absolute inset-0 flex items-center justify-center bg-black/50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity gap-2">
            <label class="cursor-pointer text-gray-200 hover:text-gold text-xs">
              <Upload class="w-4 h-4 mx-auto mb-0.5" />
              <input type="file" accept="image/*" class="hidden" @change="onImageUpload" />
            </label>
            <button type="button" class="text-gray-200 hover:text-danger text-xs" @click="removeImage"><X class="w-4 h-4" /></button>
          </div>
        </div>
        <div v-else class="w-24 h-24 rounded-md border-2 border-dashed border-border-inner flex items-center justify-center cursor-pointer hover:border-gold/50 transition-colors" @click="$refs.imageInput?.click()">
          <div class="text-center">
            <Upload class="w-5 h-5 text-gray-500 mx-auto mb-1" />
            <span class="text-xs text-gray-500">上传</span>
          </div>
          <input ref="imageInput" type="file" accept="image/*" class="hidden" @change="onImageUpload" />
        </div>
      </div>

      <div>
        <label class="block text-sm text-gray-400 mb-1">搜索关键词（逗号分隔，用于粘贴导入匹配）</label>
        <input v-model="form.search_keywords" type="text" placeholder="如: 立牌计数器, 怪物底座, 磁吸" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
      </div>

      <!-- Bundle items (only for bundle) -->
      <div v-if="isBundleCategory()">
        <label class="block text-sm text-gray-400 mb-2">子商品列表</label>
        <div class="space-y-2">
          <div v-for="(item, idx) in form.bundle_items" :key="idx" class="flex gap-2 items-center">
            <select v-model.number="form.bundle_items[idx]" class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50">
              <option :value="null" disabled>选择子商品...</option>
              <option v-for="p in bundleCandidates" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <button type="button" class="shrink-0 px-2 py-2 text-xs btn-danger rounded" @click="form.bundle_items.splice(idx, 1)"><X class="w-4 h-4" /></button>
          </div>
        </div>
        <button type="button" class="mt-2 px-3 py-1 text-xs text-gold-muted hover:text-gold border border-border-inner rounded-md" @click="form.bundle_items.push(null)">+ 添加子商品</button>
      </div>

      <!-- Contents -->
      <div>
        <label class="block text-sm text-gray-400 mb-2">内容物</label>
        <div class="space-y-2">
          <div v-for="(item, idx) in form.contents" :key="idx" class="flex gap-2">
            <input v-model="form.contents[idx]" type="text" placeholder="如: 计数器 x1" class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
            <button type="button" class="shrink-0 px-2 py-2 text-xs btn-danger rounded" @click="form.contents.splice(idx, 1)"><X class="w-4 h-4" /></button>
          </div>
        </div>
        <button type="button" class="mt-2 px-3 py-1 text-xs text-gold-muted hover:text-gold border border-border-inner rounded-md" @click="form.contents.push('')">+ 添加内容物</button>
      </div>

      <!-- Color Configuration -->
      <div>
        <label class="block text-sm text-gray-400 mb-2">配色配置</label>

        <div class="flex gap-3 mb-3">
          <label v-for="m in [{v:'fixed',l:'固定配色'},{v:'optional',l:'可选配色'}]" :key="m.v"
            class="flex items-center gap-1.5 text-sm cursor-pointer"
            :class="colorMode === m.v ? 'text-gold' : 'text-gray-400 hover:text-gray-200'"
          >
            <input v-model="colorMode" type="radio" :value="m.v" class="accent-gold" />
            {{ m.l }}
          </label>
        </div>

        <div v-if="colorMode === 'fixed'" class="flex flex-wrap gap-2">
          <button
            v-for="c in colors"
            :key="c.color_id"
            type="button"
            class="color-pill"
            :class="{ selected: selectedFixedColorId === c.color_id }"
            @click="selectFixedColor(c.color_id)"
          >
            <span v-for="(sw, i) in c.swatches" :key="i" class="w-3.5 h-3.5 rounded-sm ring-1 ring-border-inner/30" :style="{ backgroundColor: sw }"></span>
            {{ c.name }}
          </button>
        </div>

        <div v-if="colorMode === 'optional'" class="flex flex-wrap gap-2">
          <button
            v-for="c in colors"
            :key="c.color_id"
            type="button"
            class="color-pill"
            :class="{ selected: optionalColorSelected(c.color_id) }"
            @click="toggleOptionalColor(c.color_id)"
          >
            <span v-for="(sw, i) in c.swatches" :key="i" class="w-3.5 h-3.5 rounded-sm ring-1 ring-border-inner/30" :style="{ backgroundColor: sw }"></span>
            {{ c.name }}
            <span v-if="optionalColorSelected(c.color_id) && selectedOptionalColorIds[0] === c.color_id" class="text-xs text-gold ml-0.5">默认</span>
          </button>
        </div>

        <div v-if="colorMode !== 'none'" class="mt-3 p-3 bg-dark-input rounded-md">
          <div class="text-xs text-gray-500 mb-1">
            {{ colorMode === 'fixed' ? '预览: ' + (colors.find(c => c.color_id === selectedFixedColorId)?.name || '未选择') : '已选 ' + selectedOptionalColorIds.length + ' 个配色' }}
          </div>
          <div class="flex gap-1.5">
            <template v-if="colorMode === 'fixed' && selectedFixedColorId">
              <span v-for="(sw, i) in (colors.find(c => c.color_id === selectedFixedColorId)?.swatches || [])" :key="i" class="w-6 h-6 rounded ring-1 ring-border-inner/40" :style="{ backgroundColor: sw }"></span>
            </template>
            <template v-if="colorMode === 'optional'">
              <div v-for="cid in selectedOptionalColorIds" :key="cid" class="flex gap-0.5 p-1 bg-dark-card rounded ring-1 ring-border-inner/30">
                <span v-for="(sw, si) in (colors.find(c => c.color_id === cid)?.swatches || [])" :key="si" class="w-5 h-5 rounded-sm ring-1 ring-border-inner/40" :style="{ backgroundColor: sw }"></span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </form>

    <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
      <button class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors" @click="close">取消</button>
      <button class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md hover:bg-gold/30 transition-colors disabled:opacity-50" :disabled="saving" @click="handleSubmit">
        {{ saving ? '保存中...' : '保存' }}
      </button>
    </div>

    <ImageCropModal
      v-model="cropModalVisible"
      :src="cropSrc"
      :filename="cropFilename"
      @uploaded="fn => form.image = fn"
    />
  </ModalShell>
</template>

<style scoped>
.btn-danger {
  color: var(--badge-danger-text);
}
.btn-danger:hover {
  background: var(--badge-danger-bg);
}

.color-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--app-input);
  border: 1px solid var(--app-border-light);
  color: var(--app-text-dim);
}
.color-pill:hover {
  border-color: var(--app-border);
  color: var(--app-text);
}
.color-pill.selected {
  border-color: var(--app-accent);
  color: var(--app-accent);
  background: color-mix(in srgb, var(--app-accent) 12%, transparent);
}
</style>
