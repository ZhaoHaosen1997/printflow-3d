import { ref } from 'vue'
import { useApi } from './useApi'

// Settings 页 games/categories 两段复制粘贴 CRUD 的收敛（模板通过解构重命名保持不变）
export function useSimpleCrud(resource, { emptyForm, toForm, label = '' }) {
  const { get, post, put, del } = useApi()

  const items = ref([])
  const editingId = ref(null)
  const form = ref({ ...emptyForm })
  const saving = ref(false)

  async function fetchItems() {
    items.value = await get(`/api/${resource}`)
  }

  function startEdit(item) {
    editingId.value = item.id
    form.value = toForm(item)
  }

  function cancelEdit() {
    editingId.value = null
    form.value = { ...emptyForm }
  }

  async function saveItem(item) {
    saving.value = true
    try {
      await put(`/api/${resource}/${item.id}`, form.value)
      editingId.value = null
      await fetchItems()
    } catch {
      // 失败已由 useApi 全局 toast 提示
    } finally {
      saving.value = false
    }
  }

  async function createItem() {
    if (!form.value.name || !form.value.slug) return
    saving.value = true
    try {
      await post(`/api/${resource}`, form.value)
      form.value = { ...emptyForm }
      await fetchItems()
    } catch {
      // 失败已由 useApi 全局 toast 提示
    } finally {
      saving.value = false
    }
  }

  async function archiveItem(item) {
    if (!confirm(`确定归档${label} "${item.name}"？`)) return
    await del(`/api/${resource}/${item.id}`)
    await fetchItems()
  }

  return { items, editingId, form, saving, fetchItems, startEdit, cancelEdit, saveItem, createItem, archiveItem }
}
