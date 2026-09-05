<script setup>
import { ref, onMounted } from 'vue'
import { Plus, Pencil, Trash2, X } from '@lucide/vue'
import { useApi } from '../composables/useApi'

const { get, post, put, del } = useApi()

const colors = ref([])
const standardColors = ref([])
const comboColors = ref([])
const modalVisible = ref(false)
const editingColor = ref(null)
const saving = ref(false)

const form = ref({
  name: '',
  type: 'standard',
  swatches: ['#000000'],
  combo_of: [],
})
const comboPickerOpen = ref(false)

function initForm() {
  form.value = {
    name: '',
    type: 'standard',
    swatches: ['#000000'],
    combo_of: [],
  }
  comboPickerOpen.value = false
}

async function fetchColors() {
  colors.value = await get('/api/colors')
  standardColors.value = colors.value.filter(c => c.type === 'standard')
  comboColors.value = colors.value.filter(c => c.type === 'combo')
}

function openCreate() {
  editingColor.value = null
  initForm()
  modalVisible.value = true
}

function editColor(color) {
  editingColor.value = color
  form.value = {
    name: color.name,
    type: color.type,
    swatches: [...color.swatches],
    combo_of: color.combo_of ? [...color.combo_of] : [],
  }
  comboPickerOpen.value = false
  updateComboPreview()
  modalVisible.value = true
}

async function confirmDelete(color) {
  if (!confirm(`确定删除颜色 "${color.name}"？`)) return
  try {
    await del(`/api/colors/${color.id}`)
    fetchColors()
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

function addSwatch() {
  if (form.value.type === 'standard' && form.value.swatches.length >= 3) return
  form.value.swatches.push('#000000')
}

function removeSwatch(idx) {
  if (form.value.swatches.length > 1) {
    form.value.swatches.splice(idx, 1)
  }
}

function toggleComboMember(colorId) {
  const idx = form.value.combo_of.indexOf(colorId)
  if (idx >= 0) {
    form.value.combo_of.splice(idx, 1)
  } else {
    form.value.combo_of.push(colorId)
  }
  updateComboPreview()
}

function isComboMember(colorId) {
  return form.value.combo_of.includes(colorId)
}

const comboPreviewSwatches = ref([])
function updateComboPreview() {
  comboPreviewSwatches.value = form.value.combo_of.flatMap(cid => {
    const sc = standardColors.value.find(s => s.color_id === cid)
    return sc ? sc.swatches : []
  })
}

async function handleSubmit() {
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      type: form.value.type,
      swatches: form.value.swatches,
    }
    if (form.value.type === 'combo') {
      payload.combo_of = form.value.combo_of
    } else {
      payload.combo_of = null
    }

    if (editingColor.value) {
      await put(`/api/colors/${editingColor.value.id}`, payload)
    } else {
      await post('/api/colors', payload)
    }
    modalVisible.value = false
    fetchColors()
  } finally {
    saving.value = false
  }
}

onMounted(fetchColors)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-serif text-gold-title">配色管理</h2>
        <p class="text-sm text-gold-muted mt-1">管理商品的配色选项，标准色与组合色</p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
               hover:bg-gold/30 transition-colors text-sm"
        @click="openCreate"
      >
        <Plus class="w-4 h-4" />
        新增颜色
      </button>
    </div>

    <!-- Standard Colors Grid -->
    <div class="mb-8">
      <h3 class="text-sm text-gold-muted uppercase tracking-wider mb-3">标准色</h3>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3">
        <div
          v-for="c in standardColors"
          :key="c.id"
          class="color-card group"
          @click="editColor(c)"
        >
          <div v-if="c.swatches && c.swatches.length === 1" class="flex gap-1 mb-2">
            <span
              class="w-7 h-7 rounded ring-1 ring-border-inner/40"
              :style="{ backgroundColor: c.swatches[0] }"
            ></span>
          </div>
          <div
            v-else-if="c.swatches && c.swatches.length >= 2"
            class="w-7 h-7 rounded mb-2 ring-1 ring-border-inner/40"
            :style="{ background: `linear-gradient(to bottom right, ${c.swatches.join(', ')})` }"
          ></div>
          <div class="text-sm font-medium text-gray-200">{{ c.name }}</div>
          <div class="text-xs text-gray-500 font-mono mt-0.5">{{ c.color_id }}</div>
          <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
            <button
              class="w-6 h-6 flex items-center justify-center rounded bg-dark-card/80 text-gray-400 hover:text-gold text-xs"
              @click.stop="editColor(c)"
            >
              <Pencil class="w-3 h-3" />
            </button>
            <button
              class="w-6 h-6 flex items-center justify-center rounded bg-dark-card/80 text-gray-400 hover:text-danger text-xs"
              @click.stop="confirmDelete(c)"
            >
              <Trash2 class="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Combo Colors Grid -->
    <div>
      <h3 class="text-sm text-gold-muted uppercase tracking-wider mb-3">组合色</h3>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3">
        <div
          v-for="c in comboColors"
          :key="c.id"
          class="color-card group"
          @click="editColor(c)"
        >
          <div class="flex gap-1 mb-2">
            <span
              v-for="(sw, i) in c.swatches"
              :key="i"
              class="w-7 h-7 rounded ring-1 ring-border-inner/40"
              :style="{ backgroundColor: sw }"
            ></span>
          </div>
          <div class="text-sm font-medium text-gray-200">{{ c.name }}</div>
          <div class="text-xs text-gray-500 font-mono mt-0.5">{{ c.color_id }}</div>
          <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
            <button
              class="w-6 h-6 flex items-center justify-center rounded bg-dark-card/80 text-gray-400 hover:text-gold text-xs"
              @click.stop="editColor(c)"
            >
              <Pencil class="w-3 h-3" />
            </button>
            <button
              class="w-6 h-6 flex items-center justify-center rounded bg-dark-card/80 text-gray-400 hover:text-danger text-xs"
              @click.stop="confirmDelete(c)"
            >
              <Trash2 class="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Color Edit Modal -->
    <Teleport to="body">
      <div
        v-if="modalVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        @mousedown.self="modalVisible = false"
      >
        <div class="bg-dark-card border border-border-main rounded-lg shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border-inner">
            <h3 class="text-lg font-serif text-gold-title">
              {{ editingColor ? '编辑颜色' : '新增颜色' }}
            </h3>
            <button class="text-gray-500 hover:text-gray-300" @click="modalVisible = false">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            <!-- name -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">
                名称 <span class="text-danger">*</span>
              </label>
              <input
                v-model="form.name"
                type="text" required placeholder="如 黑色, 黑金"
                class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                       focus:outline-none focus:border-gold/50 placeholder-gray-600"
              />
            </div>

            <!-- type -->
            <div>
              <label class="block text-sm text-gray-400 mb-1">类型</label>
              <div class="flex gap-3">
                <label class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                  <input v-model="form.type" type="radio" value="standard" class="accent-gold" />
                  标准色
                </label>
                <label class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                  <input v-model="form.type" type="radio" value="combo" class="accent-gold" />
                  组合色
                </label>
              </div>
            </div>

            <!-- Swatches (standard) -->
            <div v-if="form.type === 'standard'">
              <label class="block text-sm text-gray-400 mb-2">颜色值</label>
              <div class="space-y-2">
                <div v-for="(sw, idx) in form.swatches" :key="idx" class="flex items-center gap-2">
                  <input
                    type="color"
                    v-model="form.swatches[idx]"
                    class="w-10 h-10 rounded border-2 border-border-inner cursor-pointer p-0 bg-transparent
                           [&::-webkit-color-swatch-wrapper]:p-0.5 [&::-webkit-color-swatch]:rounded [&::-webkit-color-swatch]:border-none"
                  />
                  <input
                    v-model="form.swatches[idx]"
                    type="text"
                    placeholder="#000000"
                    class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                           font-mono focus:outline-none focus:border-gold/50"
                  />
                  <button
                    v-if="form.swatches.length > 1"
                    type="button"
                    class="shrink-0 px-2 py-2 text-xs btn-danger rounded"
                    @click="removeSwatch(idx)"
                  >
                    <X class="w-4 h-4" />
                  </button>
                </div>
              </div>
              <button
                type="button"
                class="mt-2 px-3 py-1 text-xs text-gold-muted hover:text-gold border border-border-inner rounded-md"
                :class="{ 'opacity-40 pointer-events-none': form.swatches.length >= 3 }"
                @click="addSwatch"
              >
                + 添加色值 {{ form.swatches.length >= 3 ? '(最多3个)' : '' }}
              </button>
            </div>

            <!-- Combo members -->
            <div v-if="form.type === 'combo'">
              <label class="block text-sm text-gray-400 mb-2">选择组成颜色</label>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="sc in standardColors"
                  :key="sc.id"
                  type="button"
                  class="combo-pill"
                  :class="{ selected: isComboMember(sc.color_id) }"
                  @click="toggleComboMember(sc.color_id)"
                >
                  <span
                    v-for="(sw, i) in sc.swatches"
                    :key="i"
                    class="w-3.5 h-3.5 rounded-sm ring-1 ring-border-inner/30"
                    :style="{ backgroundColor: sw }"
                  ></span>
                  {{ sc.name }}
                </button>
              </div>
              <!-- Combo preview -->
              <div v-if="comboPreviewSwatches.length > 0" class="mt-3 p-3 bg-dark-input rounded-md">
                <div class="text-xs text-gray-500 mb-1">预览</div>
                <div class="flex gap-1.5">
                  <span
                    v-for="(sw, i) in comboPreviewSwatches"
                    :key="i"
                    class="w-6 h-6 rounded ring-1 ring-border-inner/40"
                    :style="{ backgroundColor: sw }"
                  ></span>
                </div>
              </div>
            </div>
          </form>

          <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
            <button
              class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
              @click="modalVisible = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                     hover:bg-gold/30 transition-colors disabled:opacity-50"
              :disabled="saving"
              @click="handleSubmit"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.color-card {
  position: relative;
  background: var(--app-card);
  border: 1px solid var(--app-border-light);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.color-card:hover {
  border-color: var(--app-border);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.combo-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--app-input);
  border: 1px solid var(--app-border-light);
  color: var(--app-text-dim);
}
.combo-pill:hover {
  border-color: var(--app-border);
  color: var(--app-text);
}
.combo-pill.selected {
  border-color: var(--app-accent);
  color: var(--app-accent);
  background: color-mix(in srgb, var(--app-accent) 12%, transparent);
}

.btn-danger {
  color: var(--badge-danger-text);
}
.btn-danger:hover {
  background: var(--badge-danger-bg);
}
</style>
