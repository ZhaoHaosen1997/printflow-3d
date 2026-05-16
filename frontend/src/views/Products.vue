<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, X } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const { loading, get, post, put, del } = useApi()

const products = ref([])
const filaments = ref([])
const allColors = ref([])
const standardColors = ref([])
const comboColors = ref([])
const categoryFilter = ref('')

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
  { key: 'name', label: '商品名称', sortable: true },
  { key: 'category', label: '分类' },
  { key: 'price_single', label: '单品售价' },
  { key: 'material_cost', label: '材料成本' },
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

const productForm = ref({
  name: '',
  category: 'counter',
  xianyu_item_id: '',
  price_single: 0,
  price_bundle: 0,
  image: '',
  bundle_items: [],
  contents: [],
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
      bundle_items: productForm.value.category === 'bundle' ? productForm.value.bundle_items : [],
      colors: buildColorsPayload(),
    }
    if (editingProduct.value) {
      const updated = await put(`/api/products/${editingProduct.value.id}`, payload)
      const idx = products.value.findIndex(p => p.id === editingProduct.value.id)
      if (idx >= 0) products.value[idx] = updated
    } else {
      const created = await post('/api/products', payload)
      products.value.push(created)
    }
    productModalVisible.value = false
  } finally {
    productSaving.value = false
  }
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
        try { await del(`/api/recipe-filaments/${rf.id}`) } catch {}
      }
      for (const f of filaments) {
        try { await post(`/api/recipes/${editingRecipe.value.id}/filaments`, f) } catch {}
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
      <button
        class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
               hover:bg-gold/30 transition-colors text-sm"
        @click="openCreate"
      >
        <Plus class="w-4 h-4" />
        新增商品
      </button>
    </div>

    <!-- Category tabs -->
    <div class="flex gap-2 mb-4">
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

    <!-- Product Table -->
    <DataTable
      :columns="columns"
      :data="filteredProducts"
      :loading="loading"
      :actions="productActions"
      empty-text="暂无商品，请点击「新增商品」创建"
    >
      <template #cell-name="{ row }">
        <div class="flex items-center gap-3">
          <div
            v-if="row.image"
            class="w-8 h-8 rounded bg-dark-input border border-border-inner flex-shrink-0 bg-cover bg-center"
            :style="{ backgroundImage: `url(${row.image})` }"
          ></div>
          <div>
            <div class="text-sm text-gray-200">{{ row.name }}</div>
            <div v-if="row.category === 'bundle' && row.bundle_items" class="text-xs text-gold-muted mt-0.5">
              子商品: {{ row.bundle_items.join(', ') }}
            </div>
          </div>
        </div>
      </template>
      <template #cell-category="{ value }">
        <StatusBadge :status="value" />
      </template>
      <template #cell-price_single="{ value }">
        <span class="text-gold-price font-medium">¥{{ Number(value).toFixed(2) }}</span>
      </template>
      <template #cell-material_cost="{ value }">
        <span class="text-gray-500 text-sm">¥{{ Number(value).toFixed(2) }}</span>
      </template>
    </DataTable>

    <!-- Product Form Modal (custom, with color selector) -->
    <Teleport to="body">
      <div
        v-if="productModalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @click.self="productModalVisible = false"
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
            <div class="grid grid-cols-2 gap-4">
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

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gray-400 mb-1">单品售价 <span class="text-red-400">*</span></label>
                <input v-model.number="productForm.price_single" type="number" step="0.01" min="0" required class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
              <div v-if="productForm.category !== 'bundle'">
                <label class="block text-sm text-gray-400 mb-1">合集优惠价</label>
                <input v-model.number="productForm.price_bundle" type="number" step="0.01" min="0" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">闲鱼商品ID</label>
              <input v-model="productForm.xianyu_item_id" type="text" placeholder="未上架可留空" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
            </div>

            <div>
              <label class="block text-sm text-gray-400 mb-1">图片文件名</label>
              <input v-model="productForm.image" type="text" placeholder="如 product.jpg" class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm focus:outline-none focus:border-gold/50 placeholder-gray-600" />
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
                    <template v-for="cid in selectedOptionalColorIds">
                      <span v-for="(sw, si) in (allColors.find(c => c.color_id === cid)?.swatches || [])" :key="cid+'-'+si" class="w-6 h-6 rounded ring-1 ring-border-inner/40" :style="{ backgroundColor: sw }"></span>
                    </template>
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
        @click.self="recipeModalVisible = false"
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
              class="flex items-center justify-between p-4 bg-dark-input rounded-lg border border-border-inner"
            >
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-gray-200">{{ r.name }}</span>
                  <span v-if="r.is_default" class="text-xs px-1.5 py-0.5 rounded bg-gold/20 text-gold">默认</span>
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
        @click.self="recipeFormVisible = false"
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
            <div class="grid grid-cols-2 gap-4">
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
