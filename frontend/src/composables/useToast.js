import { ref } from 'vue'

// 模块级单例（与 useTheme 同模式）：全站共享一个 toast 队列。
// useApi 在请求失败时自动调用 error()，各视图也可直接 useToast() 主动提示。
const toasts = ref([])
let seq = 0

function push(type, message, duration) {
  const id = ++seq
  toasts.value.push({ id, type, message })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
}

function dismiss(id) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx >= 0) toasts.value.splice(idx, 1)
}

const toastApi = {
  toasts,
  dismiss,
  success: (msg, duration = 2500) => push('success', msg, duration),
  error: (msg, duration = 4000) => push('error', msg, duration),
  info: (msg, duration = 3000) => push('info', msg, duration),
}

export function useToast() {
  return toastApi
}
