import { ref, readonly, onMounted, onUnmounted } from 'vue'

const isMobile = ref(false)

let installed = false
let mql = null

function handleChange(e) {
  isMobile.value = e.matches
}

function install() {
  if (installed) return
  installed = true
  mql = window.matchMedia('(max-width: 767px)')
  isMobile.value = mql.matches
  mql.addEventListener('change', handleChange)
}

export function useBreakpoint() {
  if (!installed) install()
  return { isMobile: readonly(isMobile) }
}
