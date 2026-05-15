import { ref, watchEffect } from 'vue'

const THEME_KEY = 'printflow-theme'

export const themes = [
  { id: 'workshop', name: '打印工坊', colors: ['#f5f7f5', '#0d9488'] },
  { id: 'dark-gold', name: '诡镇暗金', colors: ['#0d0d0d', '#d4af37'] },
  { id: 'github-light', name: 'GitHub 浅色', colors: ['#ffffff', '#0969da'] },
  { id: 'mono-light', name: '极简黑白', colors: ['#fafafa', '#171717'] },
]

const current = ref(localStorage.getItem(THEME_KEY) || 'workshop')

export function useTheme() {
  watchEffect(() => {
    document.documentElement.dataset.theme = current.value
    localStorage.setItem(THEME_KEY, current.value)
  })

  function setTheme(id) {
    current.value = id
  }

  return {
    themes,
    currentTheme: current,
    setTheme,
  }
}
