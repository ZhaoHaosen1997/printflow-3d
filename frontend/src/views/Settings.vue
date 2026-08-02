<script setup>
import { ref, onMounted } from 'vue'
import { Save, Plus, Pencil, Trash2, X, Check } from '@lucide/vue'
import { useApi } from '../composables/useApi'

const { loading, get, put, post, del } = useApi()
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

// ============ Games Management ============

const games = ref([])
const gameEditing = ref(null)
const gameForm = ref({ name: '', slug: '', icon: '', sort_order: 0 })
const gameSaving = ref(false)

async function fetchGames() {
  games.value = await get('/api/games')
}

function startEditGame(game) {
  gameEditing.value = game.id
  gameForm.value = { name: game.name, slug: game.slug, icon: game.icon || '', sort_order: game.sort_order }
}

function cancelEditGame() {
  gameEditing.value = null
  gameForm.value = { name: '', slug: '', icon: '', sort_order: 0 }
}

async function saveGame(game) {
  gameSaving.value = true
  try {
    await put(`/api/games/${game.id}`, gameForm.value)
    gameEditing.value = null
    await fetchGames()
  } catch (e) {
    alert('保存失败: ' + (e.message || e))
  } finally {
    gameSaving.value = false
  }
}

async function createGame() {
  if (!gameForm.value.name || !gameForm.value.slug) return
  gameSaving.value = true
  try {
    await post('/api/games', gameForm.value)
    gameForm.value = { name: '', slug: '', icon: '', sort_order: 0 }
    await fetchGames()
  } catch (e) {
    alert('创建失败: ' + (e.message || e))
  } finally {
    gameSaving.value = false
  }
}

async function archiveGame(game) {
  if (!confirm(`确定归档游戏 "${game.name}"？`)) return
  await del(`/api/games/${game.id}`)
  await fetchGames()
}

// ============ Categories Management ============

const categories = ref([])
const catEditing = ref(null)
const catForm = ref({ name: '', slug: '', sort_order: 0 })
const catSaving = ref(false)

async function fetchCategories() {
  categories.value = await get('/api/categories')
}

function startEditCat(cat) {
  catEditing.value = cat.id
  catForm.value = { name: cat.name, slug: cat.slug, sort_order: cat.sort_order }
}

function cancelEditCat() {
  catEditing.value = null
  catForm.value = { name: '', slug: '', sort_order: 0 }
}

async function saveCat(cat) {
  catSaving.value = true
  try {
    await put(`/api/categories/${cat.id}`, catForm.value)
    catEditing.value = null
    await fetchCategories()
  } catch (e) {
    alert('保存失败: ' + (e.message || e))
  } finally {
    catSaving.value = false
  }
}

async function createCat() {
  if (!catForm.value.name || !catForm.value.slug) return
  catSaving.value = true
  try {
    await post('/api/categories', catForm.value)
    catForm.value = { name: '', slug: '', sort_order: 0 }
    await fetchCategories()
  } catch (e) {
    alert('创建失败: ' + (e.message || e))
  } finally {
    catSaving.value = false
  }
}

async function archiveCat(cat) {
  if (!confirm(`确定归档分类 "${cat.name}"？`)) return
  await del(`/api/categories/${cat.id}`)
  await fetchCategories()
}

onMounted(() => {
  fetchSettings()
  fetchGames()
  fetchCategories()
})
</script>

<template>
  <div class="space-y-8">
    <div>
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-2xl font-serif text-gold-title">全局配置</h2>
          <p class="text-sm text-gold-muted mt-1">新建订单时自动套用的默认值</p>
        </div>
        <div
          v-if="saved"
          class="text-sm text-success flex items-center gap-1"
        >
          <span class="inline-block w-1.5 h-1.5 rounded-full bg-success"></span>
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

    <!-- Games Management -->
    <div>
      <h2 class="text-2xl font-serif text-gold-title mb-2">游戏管理</h2>
      <p class="text-sm text-gold-muted mb-4">商品可关联多个游戏，用于筛选和长图分组</p>

      <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border-inner text-gray-400">
              <th class="px-4 py-3 text-left font-medium">名称</th>
              <th class="px-4 py-3 text-left font-medium">Slug</th>
              <th class="px-4 py-3 text-left font-medium">排序</th>
              <th class="px-4 py-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="game in games" :key="game.id" class="border-b border-border-inner/50 hover:bg-dark-input/30">
              <td class="px-4 py-3">
                <template v-if="gameEditing === game.id">
                  <input v-model="gameForm.name" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                </template>
                <template v-else>{{ game.name }}</template>
              </td>
              <td class="px-4 py-3">
                <template v-if="gameEditing === game.id">
                  <input v-model="gameForm.slug" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                </template>
                <template v-else class="text-gray-500">{{ game.slug }}</template>
              </td>
              <td class="px-4 py-3">
                <template v-if="gameEditing === game.id">
                  <input v-model.number="gameForm.sort_order" type="number" class="w-20 px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                </template>
                <template v-else>{{ game.sort_order }}</template>
              </td>
              <td class="px-4 py-3 text-right">
                <template v-if="gameEditing === game.id">
                  <button @click="saveGame(game)" :disabled="gameSaving" class="p-1 text-success hover:text-success"><Check class="w-4 h-4" /></button>
                  <button @click="cancelEditGame" class="p-1 text-gray-500 hover:text-gray-300"><X class="w-4 h-4" /></button>
                </template>
                <template v-else>
                  <button @click="startEditGame(game)" class="p-1 text-gray-400 hover:text-gold"><Pencil class="w-4 h-4" /></button>
                  <button @click="archiveGame(game)" class="p-1 text-gray-400 hover:text-danger"><Trash2 class="w-4 h-4" /></button>
                </template>
              </td>
            </tr>
            <tr class="hover:bg-dark-input/30">
              <td class="px-4 py-3">
                <input v-model="gameForm.name" placeholder="新游戏名称" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" :disabled="gameEditing !== null" />
              </td>
              <td class="px-4 py-3">
                <input v-model="gameForm.slug" placeholder="slug" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" :disabled="gameEditing !== null" />
              </td>
              <td class="px-4 py-3">
                <input v-model.number="gameForm.sort_order" type="number" class="w-20 px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" :disabled="gameEditing !== null" />
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="createGame" :disabled="gameSaving || !gameForm.name || !gameForm.slug || gameEditing !== null" class="p-1 text-gold hover:text-gold/80 disabled:opacity-30"><Plus class="w-4 h-4" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Categories Management -->
    <div>
      <h2 class="text-2xl font-serif text-gold-title mb-2">分类管理</h2>
      <p class="text-sm text-gold-muted mb-4">全局分类，所有游戏共用</p>

      <div class="bg-dark-card border border-border-inner rounded-lg overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border-inner text-gray-400">
              <th class="px-4 py-3 text-left font-medium">名称</th>
              <th class="px-4 py-3 text-left font-medium">Slug</th>
              <th class="px-4 py-3 text-left font-medium">排序</th>
              <th class="px-4 py-3 text-right font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cat in categories" :key="cat.id" class="border-b border-border-inner/50 hover:bg-dark-input/30">
              <td class="px-4 py-3">
                <template v-if="catEditing === cat.id">
                  <input v-model="catForm.name" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                </template>
                <template v-else>{{ cat.name }}</template>
              </td>
              <td class="px-4 py-3">
                <template v-if="catEditing === cat.id">
                  <input v-model="catForm.slug" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                </template>
                <template v-else class="text-gray-500">{{ cat.slug }}</template>
              </td>
              <td class="px-4 py-3">
                <template v-if="catEditing === cat.id">
                  <input v-model.number="catForm.sort_order" type="number" class="w-20 px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" />
                </template>
                <template v-else>{{ cat.sort_order }}</template>
              </td>
              <td class="px-4 py-3 text-right">
                <template v-if="catEditing === cat.id">
                  <button @click="saveCat(cat)" :disabled="catSaving" class="p-1 text-success hover:text-success"><Check class="w-4 h-4" /></button>
                  <button @click="cancelEditCat" class="p-1 text-gray-500 hover:text-gray-300"><X class="w-4 h-4" /></button>
                </template>
                <template v-else>
                  <button @click="startEditCat(cat)" class="p-1 text-gray-400 hover:text-gold"><Pencil class="w-4 h-4" /></button>
                  <button @click="archiveCat(cat)" class="p-1 text-gray-400 hover:text-danger"><Trash2 class="w-4 h-4" /></button>
                </template>
              </td>
            </tr>
            <tr class="hover:bg-dark-input/30">
              <td class="px-4 py-3">
                <input v-model="catForm.name" placeholder="新分类名称" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" :disabled="catEditing !== null" />
              </td>
              <td class="px-4 py-3">
                <input v-model="catForm.slug" placeholder="slug" class="w-full px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" :disabled="catEditing !== null" />
              </td>
              <td class="px-4 py-3">
                <input v-model.number="catForm.sort_order" type="number" class="w-20 px-2 py-1 bg-dark-input border border-border-inner rounded text-gray-200 text-sm focus:outline-none focus:border-gold/50" :disabled="catEditing !== null" />
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="createCat" :disabled="catSaving || !catForm.name || !catForm.slug || catEditing !== null" class="p-1 text-gold hover:text-gold/80 disabled:opacity-30"><Plus class="w-4 h-4" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
