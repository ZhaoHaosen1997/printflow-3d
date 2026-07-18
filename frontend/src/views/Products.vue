<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { Plus, X, Package, Star, Upload, Crop, GripVertical, ArrowUpDown, Check } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import draggable from 'vuedraggable'

const { loading, get, post, put, del } = useApi()

const products = ref([])
const filaments = ref([])
const allColors = ref([])
const standardColors = ref([])
const comboColors = ref([])
const categoryFilter = ref('')
const sortMode = ref(false)
const sortSaving = ref(false)
const sortList = ref([])

const categories = [
  { value: '', label: '全部' },
  { value: 'counter', label: '计数器' },
  { value: 'token', label: '指示物' },
  { value: 'other', label: '其他' },
  { value: 'bundle', label: '合集' },
]

const filteredProducts = computed(() => {
  const active = products.value.filter(p => p.status === 'active')
  if (!categoryFilter.value) return active
  return active.filter(p => p.category === categoryFilter.value)
})

const columns = [
  { key: 'name', label: '商品名称', sortable: true, mobileLabel: '名称' },
  { key: 'category', label: '分类', mobileHidden: true },
  { key: 'price_single', label: '单品售价', mobileLabel: '售价' },
  { key: 'price_bundle', label: '合集价', mobileHidden: true },
  { key: 'material_cost', label: '材料成本', mobileLabel: '成本' },
]

const productActions = [
  { label: '编辑', handler: editProduct, class: 'btn-outline' },
  { label: '配方', handler: openRecipes, class: 'btn-soft' },
  { label: '归档', handler: archiveProduct, condition: (r) => r.status === 'active', class: 'btn-danger-outline' },
]

const productModalVisible = ref(false)
const editingProduct = ref(null)
const productSaving = ref(false)

const recipeModalVisible = ref(false)
const recipeProduct = ref(null)
const recipes = ref([])
const recipeSaving = ref(false)
const recipeFormVisible = ref(false)
const editingRecipe = ref(null)

const recipeForm = ref({
  name: '',
  output_qty: 1,
  print_time_min: null,
  notes: '',
  is_default: false,
  filaments: [],
})

const imageUploading = ref(false)
const cropModalVisible = ref(false)
const cropSrc = ref('')
const cropFilename = ref('')
const cropCropper = ref(null)
const cropImageEl = ref(null)

const productForm = ref({
  name: '',
  category: 'counter',
  xianyu_item_id: '',
  price_single: 0,
  price_bundle: 0,
  image: '',
  bundle_items: [],
  contents: [],
  charity_rate: '',
  search_keywords: '',
})

// color selector state
const colorMode = ref('fixed') // 'fixed' | 'optional'
const selectedFixedColorId = ref(null)
const selectedOptionalColorIds = ref([])

// all active products for bundle_items selector
const allActive = computed(() => products.value.filter(p => p.status === 'active' && p.category !== 'bundle'))

function resetProductForm() {
  productForm.value = {
    name: '',
    category: 'counter',
    xianyu_item_id: '',
    price_single: 0,
    price_bundle: 0,
    image: '',
    bundle_items: [],
    contents: [],
    charity_rate: '',
    search_keywords: '',
  }
  colorMode.value = 'fixed'
  selectedFixedColorId.value = null
  selectedOptionalColorIds.value = []
}

function selectFixedColor(colorId) {
  selectedFixedColorId.value = colorId
}

function toggleOptionalColor(colorId) {
  const idx = selectedOptionalColorIds.value.indexOf(colorId)
  if (idx >= 0) {
    selectedOptionalColorIds.value.splice(idx, 1)
  } else {
    selectedOptionalColorIds.value.push(colorId)
  }
}

function optionalColorSelected(colorId) {
  return selectedOptionalColorIds.value.includes(colorId)
}

function buildColorsPayload() {
  if (colorMode.value === 'fixed' && selectedFixedColorId.value) {
    const cs = allColors.value.find(c => c.color_id === selectedFixedColorId.value)
    return {
      type: '固定',
      colorSetId: selectedFixedColorId.value,
      swatches: cs ? cs.swatches : [],
      label: cs ? cs.name : selectedFixedColorId.value,
    }
  }
  if (colorMode.value === 'optional' && selectedOptionalColorIds.value.length > 0) {
    const swatches = selectedOptionalColorIds.value.flatMap(id => {
      const cs = allColors.value.find(c => c.color_id === id)
      return cs ? cs.swatches : []
    })
    const defaultId = selectedOptionalColorIds.value[0]
    const defaultCs = allColors.value.find(c => c.color_id === defaultId)
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

async function fetchAll() {
  const [prods, fils, colors] = await Promise.all([
    get('/api/products'),
    get('/api/filaments'),
    get('/api/colors'),
  ])
  products.value = prods
  filaments.value = fils
  allColors.value = colors
  standardColors.value = colors.filter(c => c.type === 'standard')
  comboColors.value = colors.filter(c => c.type === 'combo')
}

async function saveSortOrder() {
  sortSaving.value = true
  try {
    const items = sortList.value.map((p, idx) => ({ id: p.id, sort_order: idx }))
    await put('/api/products/sort-order', { items })
    sortMode.value = false
    await fetchAll()
  } catch (e) {
    alert('排序保存失败: ' + (e.message || e))
  } finally {
    sortSaving.value = false
  }
}

function enterSortMode() {
  sortList.value = [...filteredProducts.value]
  sortMode.value = true
}

function cancelSort() {
  sortMode.value = false
  sortList.value = []
}

// --- Product CRUD ---

function openCreate() {
  editingProduct.value = null
  resetProductForm()
  productModalVisible.value = true
}

function editProduct(row) {
  editingProduct.value = row
  productForm.value = {
    name: row.name,
    category: row.category,
    xianyu_item_id: row.xianyu_item_id || '',
    price_single: row.price_single,
    price_bundle: row.price_bundle,
    image: row.image || '',
    bundle_items: row.bundle_items ? [...row.bundle_items] : [],
    contents: row.contents ? [...row.contents] : [],
    charity_rate: row.charity_rate != null ? String(row.charity_rate) : '',
    search_keywords: row.search_keywords ? row.search_keywords.join(', ') : '',
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
  productModalVisible.value = true
}

async function archiveProduct(row) {
  if (!confirm(`确定归档商品 "${row.name}"？`)) return
  await del(`/api/products/${row.id}`)
  row.status = 'archived'
}

async function handleProductSubmit() {
  productSaving.value = true
  try {
    const payload = {
      ...productForm.value,
      charity_rate: productForm.value.charity_rate ? Number(productForm.value.charity_rate) : null,
      bundle_items: productForm.value.category === 'bundle' ? productForm.value.bundle_items : [],
      colors: buildColorsPayload(),
      search_keywords: productForm.value.search_keywords
        ? productForm.value.search_keywords.split(/[,，]/).map(s => s.trim()).filter(Boolean)
        : null,
    }
    if (payload.xianyu_item_id === '') payload.xianyu_item_id = null
    if (editingProduct.value) {
      const updated = await put(`/api/products/${editingProduct.value.id}`, payload)
      const idx = products.value.findIndex(p => p.id === editingProduct.value.id)
      if (idx >= 0) products.value[idx] = updated
    } else {
      const created = await post('/api/products', payload)
      products.value.push(created)
    }
    productModalVisible.value = false
  } catch (e) {
    alert('保存失败: ' + (e.message || e))
  } finally {
    productSaving.value = false
  }
}

async function handleImageUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    cropSrc.value = e.target.result
    cropFilename.value = file.name
    cropModalVisible.value = true
    nextTick(() => {
      if (cropImageEl.value) {
        if (cropCropper.value) cropCropper.value.destroy()
        cropCropper.value = new Cropper(cropImageEl.value, {
          aspectRatio: 1,
          viewMode: 1,
          dragMode: 'move',
          autoCropArea: 0.9,
          responsive: true,
        })
      }
    })
  }
  reader.readAsDataURL(file)
  event.target.value = ''
}

async function confirmCrop() {
  if (!cropCropper.value) return
  const canvas = cropCropper.value.getCroppedCanvas({ width: 600, height: 600, fillColor: '#fff' })
  if (!canvas) return
  canvas.toBlob(async (blob) => {
    if (!blob) return
    imageUploading.value = true
    try {
      const formData = new FormData()
      formData.append('file', blob, cropFilename.value)
      const res = await fetch('/api/products/upload-image', { method: 'POST', body: formData })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      productForm.value.image = data.filename
      cropModalVisible.value = false
    } catch (e) {
      alert('上传失败: ' + e.message)
    } finally {
      imageUploading.value = false
    }
  }, 'image/jpeg', 0.92)
}

function cancelCrop() {
  cropModalVisible.value = false
  if (cropCropper.value) {
    cropCropper.value.destroy()
    cropCropper.value = null
  }
}

function removeImage() {
  productForm.value.image = ''
}

// --- Recipe sub-view ---

async function openRecipes(row) {
  recipeProduct.value = row
  recipes.value = await get(`/api/products/${row.id}/recipes`)
  recipeModalVisible.value = true
}

function openRecipeCreate() {
  editingRecipe.value = null
  resetRecipeForm()
  recipeFormVisible.value = true
}

function editRecipe(recipe) {
  editingRecipe.value = recipe
  recipeForm.value = {
    name: recipe.name,
    output_qty: recipe.output_qty,
    print_time_min: recipe.print_time_min,
    notes: recipe.notes || '',
    is_default: recipe.is_default,
    filaments: (recipe.recipe_filaments || []).map(rf => ({
      filament_id: rf.filament?.id || rf.filament_id,
      grams: rf.grams,
    })),
  }
  recipeFormVisible.value = true
}

function resetRecipeForm() {
  recipeForm.value = {
    name: '',
    output_qty: 1,
    print_time_min: null,
    notes: '',
    is_default: false,
    filaments: [],
  }
}

function addRecipeFilament() {
  recipeForm.value.filaments.push({ filament_id: null, grams: '' })
}

function removeRecipeFilament(idx) {
  recipeForm.value.filaments.splice(idx, 1)
}

async function deleteRecipe(recipe) {
  if (!confirm(`确定删除配方 "${recipe.name}"？`)) return
  await del(`/api/recipes/${recipe.id}`)
  recipes.value = await get(`/api/products/${recipeProduct.value.id}/recipes`)
}

async function setDefaultRecipe(recipe) {
  await put(`/api/recipes/${recipe.id}/default`, {})
  recipes.value = await get(`/api/products/${recipeProduct.value.id}/recipes`)
}

async function handleRecipeSubmit() {
  const form = recipeForm.value
  const filaments = form.filaments
    .filter(f => f.filament_id && f.grams > 0)
    .map(f => ({ filament_id: Number(f.filament_id), grams: Number(f.grams) }))

  recipeSaving.value = true
  try {
    if (editingRecipe.value) {
      const payload = {
        name: form.name,
        output_qty: form.output_qty,
        print_time_min: form.print_time_min || null,
        notes: form.notes || null,
        is_default: form.is_default,
      }
      await put(`/api/recipes/${editingRecipe.value.id}`, payload)
      // update filaments: delete all existing, re-add
      for (const rf of (editingRecipe.value.recipe_filaments || [])) {
        try { await del(`/api/recipe-filaments/${rf.id}`) } catch { /* best-effort */ }
      }
      for (const f of filaments) {
        try { await post(`/api/recipes/${editingRecipe.value.id}/filaments`, f) } catch { /* best-effort */ }
      }
    } else {
      await post(`/api/products/${recipeProduct.value.id}/recipes`, {
        name: form.name,
        output_qty: form.output_qty,
        print_time_min: form.print_time_min || null,
        notes: form.notes || null,
        is_default: form.is_default,
        filaments,
      })
    }
    recipes.value = await get(`/api/products/${recipeProduct.value.id}/recipes`)
    recipeFormVisible.value = false
  } finally {
    recipeSaving.value = false
  }
}

onMounted(fetchAll)
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">商品管理</h2>
        <p class="text-sm text-gold-muted mt-1">管理商品、分类、打印配方</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="!sortMode"
          class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gold border border-border-inner rounded-lg hover:bg-dark-card transition-colors"
          @click="enterSortMode"
        >
          <ArrowUpDown class="w-4 h-4" />
          排序
        </button>
        <template v-else>
          <button
            class="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 border border-border-inner rounded-lg hover:bg-dark-card transition-colors"
            @click="cancelSort"
          >
            取消
          </button>
          <button
            class="flex items-center gap-2 px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-lg hover:bg-gold/30 transition-colors disabled:opacity-50"
            :disabled="sortSaving"
            @click="saveSortOrder"
          >
            <Check class="w-4 h-4" />
            {{ sortSaving ? '保存中...' : '保存排序' }}
          </button>
        </template>
        <button
          v-if="!sortMode"
          class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
                 hover:bg-gold/30 transition-colors text-sm"
          @click="openCreate"
        >
          <Plus class="w-4 h-4" />
          新增商品
        </button>
      </div>
    </div>

    <!-- Category tabs -->
    <div class="flex gap-2 mb-4 overflow-x-auto pb-1">
      <button
        v-for="cat in categories"
        :key="cat.value"
        class="px-3 py-1.5 rounded-md text-sm transition-colors font-medium"
        :class="
          categoryFilter === cat.value
            ? 'bg-gold/20 text-gold border border-gold/30'
            : 'text-gray-600 hover:text-gold border border-transparent hover:bg-dark-card'
        "
        @click="categoryFilter = cat.value"
      >
        {{ cat.label }}
      </button>
    </div>

    <!-- Product Table (normal mode) -->
    <DataTable
      v-if="!sortMode"
      :columns="columns"
      :data="filteredProducts"
      :loading="loading"
      :actions="productActions"
      empty-text="暂无商品，请点击「新增商品」创建"
    >
      <template #cell-name="{ row }">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded bg-dark-input border border-border-inner flex-shrink-0 flex items-center justify-center overflow-hidden">
            <img
              v-if="row.image"
              :src="`/images/${row.image}`"
              class="w-full h-full object-cover"
              @error="$event.target.style.display='none'"
            />
            <Package v-if="!row.image" class="w-4 h-4 text-gray-500" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <div class="text-sm text-gray-200">{{ row.name }}</div>
              <span
                v-if="row.charity_rate != null"
                class="text-xs px-1.5 py-0.5 rounded bg-pink-500/15 text-pink-400 border border-pink-500/30 font-medium"
              >
                &#10084; 公益 {{ Number(row.charity_rate) * 100 }}%
              </span>
            </div>
            <div v-if="row.category === 'bundle' && row.bundle_items" class="text-xs text-gold-muted mt-0.5">
              子商品: {{ row.bundle_items.join(', ') }}
            </div>
          </div>
        </div>
      </template>
      <template #cell-category="{ value }">
        <StatusBadge :status="value" />
      </template>
      <template #cell-price_single="{ value, row }">
        <span v-if="Number(value) === 0" class="text-xs px-1.5 py-0.5 rounded bg-gray-500/15 text-gray-400 border border-gray-500/30">不单卖</span>
        <span v-else class="text-gold-price font-medium">¥{{ Number(value).toFixed(2) }}</span>
      </template>
      <template #cell-price_bundle="{ value, row }">
        <span v-if="row.category === 'bundle'" class="text-gray-500 text-sm">—</span>
        <span v-else-if="Number(value) > 0" class="text-gray-400 text-sm">¥{{ Number(value).toFixed(2) }}</span>
      </template>
      <template #cell-material_cost="{ value }">
        <span class="text-gray-500 text-sm">¥{{ Number(value).toFixed(2) }}</span>
      </template>
    </DataTable>

    <!-- Sort mode: draggable list -->
    <div v-else class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
      <div class="px-4 py-3 border-b border-border-inner text-xs font-medium text-gold-muted uppercase tracking-wider">
        拖拽商品调整顺序，完成后点击「保存排序」
      </div>
      <draggable
        v-model="sortList"
        item-key="id"
        handle=".drag-handle"
        ghost-class="opacity-30"
        animation="200"
      >
        <template #item="{ element }">
          <div class="flex items-center gap-3 px-4 py-3 border-b border-border-inner/30 hover:bg-dark-input/50 transition-colors">
            <GripVertical class="w-4 h-4 text-gray-500 drag-handle cursor-grab flex-shrink-0" />
            <div class="w-8 h-8 rounded bg-dark-input border border-border-inner flex-shrink-0 flex items-center justify-center overflow-hidden">
              <img
                v-if="element.image"
                :src="`/images/${element.image}`"
                class="w-full h-full object-cover"
                @error="$event.target.style.display='none'"
              />
              <Package v-if="!element.image" class="w-4 h-4 text-gray-500" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm text-gray-200 truncate">{{ element.name }}</div>
            </div>
            <StatusBadge :status="element.category" />
            <span v-if="Number(element.price_single) === 0" class="text-xs px-1.5 py-0.5 rounded bg-gray-500/15 text-gray-400 border border-gray-500/30">不单卖</span>
            <span v-else class="text-gold-price font-medium text-sm">¥{{ Number(element.price_single).toFixed(2) }}</span>
          </div>
        </template>
      </draggable>
      <div v-if="sortList.length === 0" class="px-4 py-12 text-center text-gray-500">
        暂无商品
      </div>
    </div>

    <!-- Product Form Modal (custom, with color selector) -->
    <Teleport to="body">
      <div
        v-if="productModalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="productModalVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-xl mx-4 max-h-[85vh] flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">
              {{ editingProduct ? '编辑商品' : '新增商品' }}
            </h3>
            <button class="text-gray-500 hover:text-gray-300" @click="productModalVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleProductSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">名称 <span class="text-red-400">*</span></label>
                <input v-model="productForm.name" type="text" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">分类 <span class="text-red-400">*</span></label>
                <select v-model="productForm.category" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50">
                  <option value="counter">计数器类</option>
                  <option value="token">指示物类</option>
                  <option value="other">其他配件</option>
                  <option value="bundle">合集</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">单品售价 <span class="text-red-400">*</span></label>
                <input v-model.number="productForm.price_single" type="number" step="0.01" min="0" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                <p class="text-xs text-gray-600 mt-1">设为 0 表示不单卖（仅作为合集子商品）</p>
              </div>
              <div v-if="productForm.category !== 'bundle'">
                <label class="block text-sm text-gray-400 mb-1">合集优惠价</label>
                <input v-model.number="productForm.price_bundle" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">公益宝贝费率</label>
              <select v-model="productForm.charity_rate" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50">
                <option value="">非公益宝贝</option>
                <option value="0.01">1%</option>
                <option value="0.50">50%</option>
                <option value="1.00">100%</option>
              </select>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">闲鱼商品ID</label>
              <input v-model="productForm.xianyu_item_id" type="text" placeholder="未上架可留空" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">商品图片</label>
              <div v-if="productForm.image" class="relative group">
                <img :src="'/images/' + productForm.image" class="w-24 h-24 rounded-md object-cover border border-border-inner" @error="$event.target.style.display='none'" />
                <div class="absolute inset-0 flex items-center justify-center bg-black/50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity gap-2">
                  <label class="cursor-pointer text-gray-200 hover:text-gold text-xs">
                    <Upload class="w-4 h-4 mx-auto mb-0.5" />
                    <input type="file" accept="image/*" class="hidden" @change="handleImageUpload" />
                  </label>
                  <button type="button" class="text-gray-200 hover:text-red-400 text-xs" @click="removeImage"><X class="w-4 h-4" /></button>
                </div>
              </div>
              <div v-else class="w-24 h-24 rounded-md border-2 border-dashed border-border-inner flex items-center justify-center cursor-pointer hover:border-gold/50 transition-colors" @click="$refs.imageInput?.click()">
                <div class="text-center">
                  <Upload class="w-5 h-5 text-gray-500 mx-auto mb-1" />
                  <span class="text-xs text-gray-500">上传</span>
                </div>
                <input ref="imageInput" type="file" accept="image/*" class="hidden" @change="handleImageUpload" />
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">搜索关键词（逗号分隔，用于粘贴导入匹配）</label>
              <input v-model="productForm.search_keywords" type="text" placeholder="如: 立牌计数器, 怪物底座, 磁吸" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
            </div>

            <!-- Bundle items (only for bundle) -->
            <div v-if="productForm.category === 'bundle'">
              <label class="block text-sm text-gray-400 mb-2">子商品列表</label>
              <div class="space-y-2">
                <div v-for="(item, idx) in productForm.bundle_items" :key="idx" class="flex gap-2 items-center">
                  <select v-model.number="productForm.bundle_items[idx]" class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50">
                    <option :value="null" disabled>选择子商品...</option>
                    <option v-for="p in allActive" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                  <button type="button" class="shrink-0 px-2 py-2 text-xs btn-danger rounded" @click="productForm.bundle_items.splice(idx, 1)"><X class="w-4 h-4" /></button>
                </div>
              </div>
              <button type="button" class="mt-2 px-3 py-1 text-xs text-gold-muted hover:text-gold border border-border-inner rounded-md" @click="productForm.bundle_items.push(null)">+ 添加子商品</button>
            </div>

            <!-- Contents -->
            <div>
              <label class="block text-sm text-gray-400 mb-2">内容物</label>
              <div class="space-y-2">
                <div v-for="(item, idx) in productForm.contents" :key="idx" class="flex gap-2">
                  <input v-model="productForm.contents[idx]" type="text" placeholder="如: 计数器 x1" class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                  <button type="button" class="shrink-0 px-2 py-2 text-xs btn-danger rounded" @click="productForm.contents.splice(idx, 1)"><X class="w-4 h-4" /></button>
                </div>
              </div>
              <button type="button" class="mt-2 px-3 py-1 text-xs text-gold-muted hover:text-gold border border-border-inner rounded-md" @click="productForm.contents.push('')">+ 添加内容物</button>
            </div>

            <!-- Color Configuration -->
            <div>
              <label class="block text-sm text-gray-400 mb-2">配色配置</label>

              <!-- Mode toggle -->
              <div class="flex gap-3 mb-3">
                <label v-for="m in [{v:'fixed',l:'固定配色'},{v:'optional',l:'可选配色'}]" :key="m.v"
                  class="flex items-center gap-1.5 text-sm cursor-pointer"
                  :class="colorMode === m.v ? 'text-gold' : 'text-gray-400 hover:text-gray-200'"
                >
                  <input v-model="colorMode" type="radio" :value="m.v" class="accent-gold" />
                  {{ m.l }}
                </label>
              </div>

              <!-- Fixed color: single select -->
              <div v-if="colorMode === 'fixed'" class="flex flex-wrap gap-2">
                <button
                  v-for="c in allColors"
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

              <!-- Optional color: multi select -->
              <div v-if="colorMode === 'optional'" class="flex flex-wrap gap-2">
                <button
                  v-for="c in allColors"
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

              <!-- Color preview -->
              <div v-if="colorMode !== 'none'" class="mt-3 p-3 bg-dark-input rounded-md">
                <div class="text-xs text-gray-500 mb-1">
                  {{ colorMode === 'fixed' ? '预览: ' + (allColors.find(c => c.color_id === selectedFixedColorId)?.name || '未选择') : '已选 ' + selectedOptionalColorIds.length + ' 个配色' }}
                </div>
                <div class="flex gap-1.5">
                  <template v-if="colorMode === 'fixed' && selectedFixedColorId">
                    <span v-for="(sw, i) in (allColors.find(c => c.color_id === selectedFixedColorId)?.swatches || [])" :key="i" class="w-6 h-6 rounded ring-1 ring-border-inner/40" :style="{ backgroundColor: sw }"></span>
                  </template>
                  <template v-if="colorMode === 'optional'">
                    <div v-for="cid in selectedOptionalColorIds" :key="cid" class="flex gap-0.5 p-1 bg-dark-card rounded ring-1 ring-border-inner/30">
                      <span v-for="(sw, si) in (allColors.find(c => c.color_id === cid)?.swatches || [])" :key="si" class="w-5 h-5 rounded-sm ring-1 ring-border-inner/40" :style="{ backgroundColor: sw }"></span>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </form>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors" @click="productModalVisible = false">取消</button>
            <button class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md hover:bg-gold/30 transition-colors disabled:opacity-50" :disabled="productSaving" @click="handleProductSubmit">
              {{ productSaving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Recipe Manager Modal -->
    <Teleport to="body">
      <div
        v-if="recipeModalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="recipeModalVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">
              {{ recipeProduct?.name }} — 打印配方
            </h3>
            <button class="text-gray-500 hover:text-gray-300 text-xl" @click="recipeModalVisible = false">&times;</button>
          </div>

          <div class="flex-1 overflow-y-auto p-6 space-y-3">
            <div v-if="recipes.length === 0" class="text-center text-gray-500 py-8">
              暂无配方，请添加
            </div>
            <div
              v-for="r in recipes"
              :key="r.id"
              class="flex items-center justify-between p-4 bg-dark-input rounded-lg border transition-colors"
              :class="r.is_default ? 'border-gold/40 shadow-[inset_0_0_0_1px_rgba(212,175,55,0.15)]' : 'border-border-inner'"
            >
              <div class="flex-1">
      <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-medium" :class="r.is_default ? 'text-gold' : 'text-gray-200'">{{ r.name }}</span>
                  <span
                    v-if="r.is_default"
                    class="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-gold/15 text-gold border border-gold/30"
                  >
                    <Star class="w-3 h-3 fill-gold" />
                    默认配方
                  </span>
                </div>
                <div class="text-xs text-gray-500 mt-1 space-x-3">
                  <span>产出: {{ r.output_qty }}件</span>
                  <span v-if="r.print_time_min">时长: {{ r.print_time_min }}分钟</span>
                  <span>已打印: {{ r.print_count }}次</span>
                </div>
                <div class="text-xs mt-1 space-x-3">
                  <span class="text-gold-price">总成本: ¥{{ Number(r.total_cost || 0).toFixed(2) }}</span>
                  <span class="text-gold-price">单位成本: ¥{{ Number(r.unit_cost || 0).toFixed(2) }}</span>
                </div>
                <div v-if="r.recipe_filaments && r.recipe_filaments.length" class="text-xs text-gray-500 mt-1">
                  耗材: {{ r.recipe_filaments.map(rf => `${rf.filament?.brand || '?'} ${rf.filament?.material || '?'} ${rf.grams}g`).join(', ') }}
                </div>
              </div>
              <div class="flex gap-2 ml-4">
                <button class="px-2 py-1 text-xs text-gold-muted hover:text-gold" @click="editRecipe(r)">编辑</button>
                <button
                  v-if="!r.is_default"
                  class="px-2 py-1 text-xs text-gold-muted hover:text-gold"
                  @click="setDefaultRecipe(r)"
                >
                  设默认
                </button>
                <button class="px-2 py-1 text-xs text-red-500 hover:text-red-400" @click="deleteRecipe(r)">删除</button>
              </div>
            </div>
          </div>

          <div class="px-6 py-4 border-t border-border-inner">
            <button
              class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
                     hover:bg-gold/30 transition-colors text-sm"
              @click="openRecipeCreate"
            >
              <Plus class="w-4 h-4" />
              新增配方
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Recipe Form Modal (custom, with filament picker) -->
    <Teleport to="body">
      <div
        v-if="recipeFormVisible"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="recipeFormVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">
              {{ editingRecipe ? '编辑配方' : '新增配方' }}
            </h3>
            <button class="text-gray-500 hover:text-gray-300" @click="recipeFormVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleRecipeSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <!-- name -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">配方名称 <span class="text-red-400">*</span></label>
              <input
                v-model="recipeForm.name"
                type="text" required placeholder="如 标准打印-单件"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
            </div>

            <!-- output_qty + print_time_min -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">单次产出数量 <span class="text-red-400">*</span></label>
                <input
                  v-model.number="recipeForm.output_qty"
                  type="number" required min="1"
                  class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                         focus:outline-none focus:border-gold/50"
                />
              </div>
              <div>
                <label class="block text-sm text-gray-400 mb-1">打印时长(分钟)</label>
                <input
                  v-model.number="recipeForm.print_time_min"
                  type="number" placeholder="可空"
                  class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                         focus:outline-none focus:border-gold/50 placeholder-gray-600"
                />
              </div>
            </div>

            <!-- notes -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">备注</label>
              <input
                v-model="recipeForm.notes"
                type="text" placeholder="可空"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
            </div>

            <!-- is_default -->
            <div class="flex items-center gap-2">
              <input v-model="recipeForm.is_default" :true-value="true" :false-value="false" type="checkbox" class="accent-gold" />
              <label class="text-sm text-gray-400">设为默认配方</label>
            </div>

            <!-- Filaments -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-sm text-gray-400">耗材用料</label>
                <button
                  type="button"
                  class="text-xs text-gold-muted hover:text-gold px-2 py-1 border border-border-inner rounded"
                  @click="addRecipeFilament"
                >
                  + 添加耗材
                </button>
              </div>
              <div v-if="recipeForm.filaments.length === 0" class="text-xs text-gray-600 py-2">
                尚未添加耗材，点击上方按钮添加
              </div>
              <div
                v-for="(rf, idx) in recipeForm.filaments"
                :key="idx"
                class="flex items-center gap-2 mb-2"
              >
                <select
                  v-model.number="rf.filament_id"
                  class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                         focus:outline-none focus:border-gold/50"
                >
                  <option :value="null" disabled>选择耗材...</option>
                  <option
                    v-for="f in filaments"
                    :key="f.id"
                    :value="f.id"
                  >
                    {{ f.brand }} {{ f.material }} (¥{{ Number(f.price_per_kg).toFixed(0) }}/kg)
                  </option>
                </select>
                <input
                  v-model.number="rf.grams"
                  type="number" step="0.1" min="0" placeholder="克数"
                  class="w-24 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                         focus:outline-none focus:border-gold/50 placeholder-gray-600"
                />
                <button
                  type="button"
                  class="shrink-0 px-2 py-2 text-xs btn-danger rounded"
                  @click="removeRecipeFilament(idx)"
                >
                  <X class="w-4 h-4" />
                </button>
              </div>
              <p class="text-xs text-gray-600 mt-1">克数输入后成本将自动计算</p>
            </div>
          </form>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="recipeFormVisible = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                     hover:bg-gold/30 transition-colors disabled:opacity-50"
              :disabled="recipeSaving"
              @click="handleRecipeSubmit"
            >
              {{ recipeSaving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Crop Modal -->
    <Teleport to="body">
      <div
        v-if="cropModalVisible"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm"
        @mousedown.self="cancelCrop"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-lg mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">裁剪图片</h3>
            <button class="text-gray-500 hover:text-gray-300" @click="cancelCrop"><X class="w-5 h-5" /></button>
          </div>
          <div class="p-4">
            <div class="max-h-[60vh] overflow-hidden bg-dark-input rounded-md">
              <img ref="cropImageEl" :src="cropSrc" class="block w-full" />
            </div>
          </div>
          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="cancelCrop"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md hover:bg-gold/30 transition-colors disabled:opacity-50"
              :disabled="imageUploading"
              @click="confirmCrop"
            >
              <span class="flex items-center gap-1.5"><Crop class="w-3.5 h-3.5" />{{ imageUploading ? '上传中...' : '确认裁剪' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
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
