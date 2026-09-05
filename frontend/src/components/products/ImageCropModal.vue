<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { Crop } from '@lucide/vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import ModalShell from '../ModalShell.vue'
import { useToast } from '../../composables/useToast'

// 图片裁剪上传弹窗：从商品表单拆出（原 Products.vue Crop Modal）
// 用法：<ImageCropModal v-model="visible" :src="cropSrc" :filename="name" @uploaded="fn => ..." />
const props = defineProps({
  modelValue: { type: Boolean, required: true },
  src: { type: String, required: true },
  filename: { type: String, default: 'image.jpg' },
})

const emit = defineEmits(['update:modelValue', 'uploaded'])

const toast = useToast()
const uploading = ref(false)
const cropper = ref(null)
const imageEl = ref(null)

watch(() => props.modelValue, (open) => {
  if (!open) {
    if (cropper.value) {
      cropper.value.destroy()
      cropper.value = null
    }
    return
  }
  nextTick(() => {
    if (imageEl.value) {
      cropper.value = new Cropper(imageEl.value, {
        aspectRatio: 1,
        viewMode: 1,
        dragMode: 'move',
        autoCropArea: 0.9,
        responsive: true,
      })
    }
  })
})

onBeforeUnmount(() => {
  if (cropper.value) cropper.value.destroy()
})

function close() {
  emit('update:modelValue', false)
}

function cancel() {
  close()
}

function confirmCrop() {
  if (!cropper.value) return
  const canvas = cropper.value.getCroppedCanvas({ width: 600, height: 600, fillColor: '#fff' })
  if (!canvas) return
  canvas.toBlob(async (blob) => {
    if (!blob) return
    uploading.value = true
    try {
      const formData = new FormData()
      formData.append('file', blob, props.filename)
      const res = await fetch('/api/products/upload-image', { method: 'POST', body: formData })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || '上传失败')
      }
      const data = await res.json()
      emit('uploaded', data.filename)
      close()
    } catch (e) {
      toast.error(e.message || '上传失败')
    } finally {
      uploading.value = false
    }
  }, 'image/jpeg', 0.92)
}
</script>

<template>
  <ModalShell
    v-if="modelValue"
    title="裁剪图片"
    width="max-w-lg"
    z="z-[60]"
    :dismissable="false"
    @close="cancel"
  >
    <div class="p-4">
      <div class="max-h-[60vh] overflow-hidden bg-dark-input rounded-md">
        <img ref="imageEl" :src="src" class="block w-full" />
      </div>
    </div>
    <div class="flex justify-end gap-3 px-6 py-4 border-t border-border-inner">
      <button
        class="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-dark-input rounded-md transition-colors"
        @click="cancel"
      >
        取消
      </button>
      <button
        class="px-4 py-2 text-sm bg-gold/20 text-gold border border-gold/40 rounded-md hover:bg-gold/30 transition-colors disabled:opacity-50"
        :disabled="uploading"
        @click="confirmCrop"
      >
        <span class="flex items-center gap-1.5"><Crop class="w-3.5 h-3.5" />{{ uploading ? '上传中...' : '确认裁剪' }}</span>
      </button>
    </div>
  </ModalShell>
</template>
