<script setup>
import { ref, watch, onMounted } from 'vue'
import { X } from '@lucide/vue'
import { useBreakpoint } from '../composables/useBreakpoint'

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, required: true },
  fields: { type: Array, required: true },
  initialData: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
  width: { type: String, default: 'max-w-lg' },
})

const emit = defineEmits(['close', 'submit'])
const { isMobile } = useBreakpoint()

const form = ref({})

function initForm() {
  const data = {}
  for (const field of props.fields) {
    data[field.name] = props.initialData[field.name] ?? field.default ?? ''
  }
  form.value = data
}

onMounted(initForm)
watch(() => props.visible, (v) => { if (v) initForm() })

function isVisible(field) {
  if (!field.visible) return true
  return field.visible(form.value)
}

function onSubmit() {
  emit('submit', { ...form.value })
}

function addArrayItem(field) {
  if (!Array.isArray(form.value[field.name])) {
    form.value[field.name] = []
  }
  form.value[field.name].push(field.itemDefault || '')
}

function removeArrayItem(field, index) {
  form.value[field.name].splice(index, 1)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      :class="isMobile ? 'flex flex-col' : 'flex items-center justify-center'"
      @click.self="emit('close')"
    >
      <div
        :class="[
          'bg-dark-card border border-border-main shadow-2xl w-full',
          isMobile
            ? 'flex flex-col h-full rounded-none border-0'
            : 'rounded-lg mx-4 ' + width
        ]"
      >
        <div class="flex items-center justify-between px-4 md:px-6 py-4 border-b border-border-inner flex-shrink-0">
          <h3 class="text-lg font-serif text-gold-title">{{ title }}</h3>
          <button class="text-gray-500 hover:text-gray-300" @click="emit('close')">
            <X class="w-5 h-5" />
          </button>
        </div>

        <form @submit.prevent="onSubmit" class="px-4 md:px-6 py-4 space-y-4 overflow-y-auto" :class="isMobile ? 'flex-1' : 'max-h-[70vh]'">
          <div v-for="field in fields" :key="field.name" v-show="isVisible(field)">
            <label class="block text-sm text-gray-400 mb-1">
              {{ field.label }}
              <span v-if="field.required" class="text-red-400">*</span>
            </label>

            <!-- text / number -->
            <input
              v-if="field.type === 'text' || field.type === 'number'"
              v-model="form[field.name]"
              :type="field.type"
              :placeholder="field.placeholder"
              :required="field.required"
              :disabled="field.disabled"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50 placeholder-gray-600 disabled:opacity-50"
            />

            <!-- select -->
            <select
              v-else-if="field.type === 'select'"
              v-model="form[field.name]"
              :required="field.required"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50"
            >
              <option value="" disabled>请选择...</option>
              <option v-for="opt in field.options" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>

            <!-- textarea -->
            <textarea
              v-else-if="field.type === 'textarea'"
              v-model="form[field.name]"
              :placeholder="field.placeholder"
              :rows="field.rows || 3"
              class="w-full px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                     focus:outline-none focus:border-gold/50 placeholder-gray-600 resize-none"
            ></textarea>

            <!-- array-input -->
            <div v-else-if="field.type === 'array-input'" class="space-y-2">
              <div v-for="(item, idx) in (form[field.name] || [])" :key="idx" class="flex gap-2">
                <input
                  v-model="form[field.name][idx]"
                  type="text"
                  class="flex-1 px-3 py-2 bg-dark-input border border-border-inner rounded-md text-gray-200 text-sm
                         focus:outline-none focus:border-gold/50"
                />
                <button
                  type="button"
                  class="px-2 py-1 text-xs btn-danger rounded transition-colors"
                  @click="removeArrayItem(field, idx)"
                >
                  删除
                </button>
              </div>
              <button
                type="button"
                class="px-3 py-1 text-xs text-gold-muted hover:text-gold border border-border-inner rounded-md"
                @click="addArrayItem(field)"
              >
                + 添加
              </button>
            </div>

            <p v-if="field.hint" class="text-xs text-gray-600 mt-1">{{ field.hint }}</p>
          </div>
        </form>

        <div class="flex justify-end gap-3 px-4 md:px-6 py-4 border-t border-border-inner flex-shrink-0">
          <button
            class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md
                   hover:bg-gold/30 transition-colors disabled:opacity-50"
            :disabled="loading"
            @click="onSubmit"
          >
            {{ loading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.btn-danger {
  color: var(--badge-danger-text);
}
.btn-danger:hover {
  background: var(--badge-danger-bg);
}
</style>
