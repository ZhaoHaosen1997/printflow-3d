import { ref } from 'vue'
import { useToast } from './useToast'

const toast = useToast()

export function useApi() {
  const loading = ref(false)
  const error = ref(null)
  let pendingCount = 0

  // silent: true 时不在全局 toast 报错（用于轮询等可预期失败场景），错误仍会抛给调用方
  async function request(endpoint, options = {}) {
    const { silent, ...fetchOptions } = options
    pendingCount++
    loading.value = true
    error.value = null
    try {
      const res = await fetch(endpoint, {
        headers: { 'Content-Type': 'application/json', ...fetchOptions.headers },
        ...fetchOptions,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        let msg = body.detail || `HTTP ${res.status}`
        // FastAPI 校验错误的 detail 是数组
        if (Array.isArray(msg)) {
          msg = msg.map(d => d.msg || JSON.stringify(d)).join('；')
        }
        error.value = msg
        throw new Error(msg)
      }
      return await res.json().catch(() => null)
    } catch (e) {
      if (!error.value) error.value = e.message
      if (!silent) {
        toast.error(e.message || '请求失败，请稍后重试')
      }
      throw e
    } finally {
      pendingCount--
      if (pendingCount === 0) loading.value = false
    }
  }

  function get(endpoint, opts) {
    return request(endpoint, opts)
  }

  function post(endpoint, body, opts) {
    return request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
      ...opts,
    })
  }

  function put(endpoint, body, opts) {
    return request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
      ...opts,
    })
  }

  function del(endpoint, body, headers, opts) {
    const options = { method: 'DELETE', ...opts }
    if (body) {
      options.body = JSON.stringify(body)
    }
    if (headers) {
      options.headers = headers
    }
    return request(endpoint, options)
  }

  return { loading, error, get, post, put, del }
}
