import { ref } from 'vue'

export function useApi() {
  const loading = ref(false)
  const error = ref(null)
  let pendingCount = 0

  async function request(endpoint, options = {}) {
    pendingCount++
    loading.value = true
    error.value = null
    try {
      const res = await fetch(endpoint, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const msg = body.detail || `HTTP ${res.status}`
        error.value = msg
        throw new Error(msg)
      }
      return await res.json()
    } catch (e) {
      if (!error.value) error.value = e.message
      throw e
    } finally {
      pendingCount--
      if (pendingCount === 0) loading.value = false
    }
  }

  function get(endpoint) {
    return request(endpoint)
  }

  function post(endpoint, body) {
    return request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  function put(endpoint, body) {
    return request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
  }

  function del(endpoint, body) {
    const options = { method: 'DELETE' }
    if (body) {
      options.body = JSON.stringify(body)
    }
    return request(endpoint, options)
  }

  return { loading, error, get, post, put, del }
}
