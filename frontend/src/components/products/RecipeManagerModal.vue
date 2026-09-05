<script setup>
import { ref, watch } from 'vue'
import { X, Plus, Star } from '@lucide/vue'
import ModalShell from '../ModalShell.vue'
import { useApi } from '../../composables/useApi'

// 配方管理弹窗：列表 + 内嵌配方表单（原 Products.vue 两个 Modal）
// 用法：<RecipeManagerModal v-model="visible" :product="row" />
const props = defineProps({
  modelValue: { type: Boolean, required: true },
  product: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue'])

const { get, post, put, del } = useApi()

const recipes = ref([])
const filaments = ref([])
const filamentsLoaded = ref(false)
const formVisible = ref(false)
const editingRecipe = ref(null)
const saving = ref(false)

const form = ref({
  name: '',
  output_qty: 1,
  print_time_min: null,
  notes: '',
  is_default: false,
  filaments: [],
})

watch(() => props.modelValue, async (open) => {
  if (!open || !props.product) return
  await loadRecipes()
  if (!filamentsLoaded.value) {
    try {
      filaments.value = await get('/api/filaments')
      filamentsLoaded.value = true
    } catch {
      // 失败已由 useApi 全局 toast 提示
    }
  }
})

async function loadRecipes() {
  try {
    recipes.value = await get(`/api/products/${props.product.id}/recipes`)
  } catch {
    // 失败已由 useApi 全局 toast 提示
  }
}

function resetForm() {
  form.value = { name: '', output_qty: 1, print_time_min: null, notes: '', is_default: false, filaments: [] }
}

function openCreate() {
  editingRecipe.value = null
  resetForm()
  formVisible.value = true
}

function openEdit(recipe) {
  editingRecipe.value = recipe
  form.value = {
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
  formVisible.value = true
}

function addFilament() {
  form.value.filaments.push({ filament_id: null, grams: '' })
}

function removeFilament(idx) {
  form.value.filaments.splice(idx, 1)
}

async function handleSubmit() {
  const f = form.value
  const filamentsPayload = f.filaments
    .filter(x => x.filament_id && x.grams > 0)
    .map(x => ({ filament_id: Number(x.filament_id), grams: Number(x.grams) }))

  saving.value = true
  try {
    if (editingRecipe.value) {
      await put(`/api/recipes/${editingRecipe.value.id}`, {
        name: f.name,
        output_qty: f.output_qty,
        print_time_min: f.print_time_min || null,
        notes: f.notes || null,
        is_default: f.is_default,
      })
      // 整单批量替换耗材（单事务，v1.19.0）——替代逐条删+建的 2N 次请求，
      // 中途失败不再静默丢失耗材关联
      await put(`/api/recipes/${editingRecipe.value.id}/filaments`, { items: filamentsPayload })
    } else {
      await post(`/api/products/${props.product.id}/recipes`, {
        name: f.name,
        output_qty: f.output_qty,
        print_time_min: f.print_time_min || null,
        notes: f.notes || null,
        is_default: f.is_default,
        filaments: filamentsPayload,
      })
    }
    formVisible.value = false
    await loadRecipes()
  } finally {
    saving.value = false
  }
}

async function removeRecipe(recipe) {
  if (!confirm(`确定删除配方 "${recipe.name}"？`)) return
  await del(`/api/recipes/${recipe.id}`)
  await loadRecipes()
}

async function setDefault(recipe) {
  await put(`/api/recipes/${recipe.id}/default`, {})
  await loadRecipes()
}

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <ModalShell
    v-if="modelValue"
    :title="`${product?.name || ''} — 打印配方`"
    width="max-w-2xl"
    @close="close"
  >
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
          <button class="px-2 py-1 text-xs text-gold-muted hover:text-gold" @click="openEdit(r)">编辑</button>
          <button
            v-if="!r.is_default"
            class="px-2 py-1 text-xs text-gold-muted hover:text-gold"
            @click="setDefault(r)"
          >
            设默认
          </button>
          <button class="px-2 py-1 text-xs text-danger hover:text-danger" @click="removeRecipe(r)">删除</button>
        </div>
      </div>
    </div>

    <div class="px-6 py-4 border-t border-border-inner">
      <button
        class="flex items-center gap-2 px-4 py-2 bg-gold/20 text-gold border border-gold/30 rounded-lg
               hover:bg-gold/30 transition-colors text-sm"
        @click="openCreate"
      >
        <Plus class="w-4 h-4" />
        新增配方
      </button>
    </div>

    <!-- Recipe Form（嵌套弹窗） -->
    <ModalShell
      v-if="formVisible"
      :title="editingRecipe ? '编辑配方' : '新增配方'"
      width="max-w-lg"
      z="z-[60]"
      @close="formVisible = false"
    >
      <form @submit.prevent="handleSubmit" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">配方名称 <span class="text-danger">*</span></label>
          <input
            v-model="form.name"
            type="text" required placeholder="如 标准打印-单件"
            class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                   focus:outline-none focus:border-gold/50 placeholder-gray-600"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">单次产出数量 <span class="text-danger">*</span></label>
            <input
              v-model.number="form.output_qty"
              type="number" required min="1"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">打印时长(分钟)</label>
            <input
              v-model.number="form.print_time_min"
              type="number" placeholder="可空"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50 placeholder-gray-600"
            />
          </div>
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-1">备注</label>
          <input
            v-model="form.notes"
            type="text" placeholder="可空"
            class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                   focus:outline-none focus:border-gold/50 placeholder-gray-600"
          />
        </div>

        <div class="flex items-center gap-2">
          <input v-model="form.is_default" :true-value="true" :false-value="false" type="checkbox" class="accent-gold" />
          <label class="text-sm text-gray-400">设为默认配方</label>
        </div>

        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm text-gray-400">耗材用料</label>
            <button
              type="button"
              class="text-xs text-gold-muted hover:text-gold px-2 py-1 border border-border-inner rounded"
              @click="addFilament"
            >
              + 添加耗材
            </button>
          </div>
          <div v-if="form.filaments.length === 0" class="text-xs text-gray-600 py-2">
            尚未添加耗材，点击上方按钮添加
          </div>
          <div
            v-for="(rf, idx) in form.filaments"
            :key="idx"
            class="flex items-center gap-2 mb-2"
          >
            <select
              v-model.number="rf.filament_id"
              class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            >
              <option :value="null" disabled>选择耗材...</option>
              <option v-for="f in filaments" :key="f.id" :value="f.id">
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
              @click="removeFilament(idx)"
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
          @click="formVisible = false"
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
    </ModalShell>
  </ModalShell>
</template>
