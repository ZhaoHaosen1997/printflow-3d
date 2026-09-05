<script setup>
import { ref, onMounted, computed } from 'vue'
import { Plus, Package, GripVertical, ArrowUpDown, Check } from '@lucide/vue'
import { useApi } from '../composables/useApi'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'
import ProductFormModal from '../components/products/ProductFormModal.vue'
import RecipeManagerModal from '../components/products/RecipeManagerModal.vue'
import DescriptionModal from '../components/products/DescriptionModal.vue'
import { formatMoney } from '../utils/format'

const { loading, get, put, del } = useApi()

const products = ref([])
const filaments = ref([])
const allColors = ref([])
const categoryFilter = ref('')
const gameFilter = ref('')
const sortMode = ref(false)
const sortSaving = ref(false)
const sortList = ref([])

const games = ref([])
const categories = ref([])

const categoryTabs = computed(() => {
  const tabs = [{ value: '', label: '全部' }]
  for (const cat of categories.value) {
    if (cat.status === 'active') {
      tabs.push({ value: String(cat.id), label: cat.name })
    }
  }
  return tabs
})

const gameTabs = computed(() => {
  const tabs = [{ value: '', label: '全部游戏' }]
  for (const game of games.value) {
    if (game.status === 'active') {
      tabs.push({ value: String(game.id), label: game.name })
    }
  }
  return tabs
})

const filteredProducts = computed(() => {
  let active = products.value.filter(p => p.status === 'active')
  if (categoryFilter.value) {
    active = active.filter(p => String(p.category_id) === categoryFilter.value)
  }
  if (gameFilter.value) {
    const gid = Number(gameFilter.value)
    active = active.filter(p => p.games && p.games.some(g => g.id === gid))
  }
  return active
})

// bundle 子商品候选：所有非合集的在售商品
const bundleCandidates = computed(() =>
  products.value.filter(p => p.status === 'active' && p.category !== 'bundle')
)

const columns = [
  { key: 'name', label: '商品名称', sortable: true, mobileLabel: '名称' },
  { key: 'category', label: '分类', mobileHidden: true, format: (val, row) => row.category_obj?.name || val },
  { key: 'price_single', label: '单品售价', mobileLabel: '售价' },
  { key: 'price_bundle', label: '合集价', mobileHidden: true },
  { key: 'material_cost', label: '材料成本', mobileLabel: '成本' },
]

// --- 子弹窗状态（表单/配方/介绍各自封装在子组件内） ---
const productModalOpen = ref(false)
const editingProduct = ref(null)
const recipeManagerOpen = ref(false)
const recipeProduct = ref(null)
const descOpen = ref(false)
const descProduct = ref(null)

const productActions = [
  { label: '编辑', handler: editProduct, class: 'btn-outline' },
  { label: '配方', handler: openRecipes, class: 'btn-soft' },
  { label: '生成介绍', handler: openDescription, condition: (r) => r.category === 'bundle', class: 'btn-ghost' },
  { label: '归档', handler: archiveProduct, condition: (r) => r.status === 'active', class: 'btn-danger-outline' },
]

async function fetchAll() {
  const [prods, fils, colors, gamesData, catsData] = await Promise.all([
    get('/api/products'),
    get('/api/filaments'),
    get('/api/colors'),
    get('/api/games'),
    get('/api/categories'),
  ])
  products.value = prods
  filaments.value = fils
  allColors.value = colors
  games.value = gamesData
  categories.value = catsData
}

async function saveSortOrder() {
  sortSaving.value = true
  try {
    const items = sortList.value.map((p, idx) => ({ id: p.id, sort_order: idx }))
    await put('/api/products/sort-order', { items })
    sortMode.value = false
    await fetchAll()
  } catch {
    // 失败已由 useApi 全局 toast 提示
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
  productModalOpen.value = true
}

function editProduct(row) {
  editingProduct.value = row
  productModalOpen.value = true
}

function onProductSaved(saved) {
  const idx = products.value.findIndex(p => p.id === saved.id)
  if (idx >= 0) products.value[idx] = saved
  else products.value.push(saved)
}

function openRecipes(row) {
  recipeProduct.value = row
  recipeManagerOpen.value = true
}

function openDescription(row) {
  descProduct.value = row
  descOpen.value = true
}

async function archiveProduct(row) {
  if (!confirm(`确定归档商品 "${row.name}"？`)) return
  await del(`/api/products/${row.id}`)
  row.status = 'archived'
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

    <!-- Game tabs -->
    <div class="flex gap-2 mb-2 overflow-x-auto pb-1">
      <button
        v-for="game in gameTabs"
        :key="'g-' + game.value"
        class="px-3 py-1.5 rounded-md text-sm transition-colors font-medium"
        :class="
          gameFilter === game.value
            ? 'bg-gold/20 text-gold border border-gold/30'
            : 'text-gray-600 hover:text-gold border border-transparent hover:bg-dark-card'
        "
        @click="gameFilter = game.value"
      >
        {{ game.label }}
      </button>
    </div>

    <!-- Category tabs -->
    <div class="flex gap-2 mb-4 overflow-x-auto pb-1">
      <button
        v-for="cat in categoryTabs"
        :key="'c-' + cat.value"
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
      <template #cell-price_single="{ value }">
        <span v-if="Number(value) === 0" class="text-xs px-1.5 py-0.5 rounded bg-gray-500/15 text-gray-400 border border-gray-500/30">不单卖</span>
        <span v-else class="text-gold-price font-medium">{{ formatMoney(value, { dash: false }) }}</span>
      </template>
      <template #cell-price_bundle="{ value, row }">
        <span v-if="row.category === 'bundle'" class="text-gray-500 text-sm">—</span>
        <span v-else-if="Number(value) > 0" class="text-gray-400 text-sm">{{ formatMoney(value, { dash: false }) }}</span>
      </template>
      <template #cell-material_cost="{ value }">
        <span class="text-gray-500 text-sm">{{ formatMoney(value, { dash: false }) }}</span>
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
            <span v-else class="text-gold-price font-medium text-sm">{{ formatMoney(element.price_single, { dash: false }) }}</span>
          </div>
        </template>
      </draggable>
      <div v-if="sortList.length === 0" class="px-4 py-12 text-center text-gray-500">
        暂无商品
      </div>
    </div>

    <!-- 子弹窗：表单 / 配方 / 介绍 -->
    <ProductFormModal
      v-model="productModalOpen"
      :product="editingProduct"
      :categories="categories"
      :games="games"
      :colors="allColors"
      :bundle-candidates="bundleCandidates"
      @saved="onProductSaved"
    />
    <RecipeManagerModal v-model="recipeManagerOpen" :product="recipeProduct" />
    <DescriptionModal v-model="descOpen" :product="descProduct" />
  </div>
</template>
