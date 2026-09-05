import { ref, computed } from 'vue'

// 分页逻辑收敛（此前 Orders/PrintTasks/Buyers 三份手写重复）
// 用法：
//   const { page, totalPages, pageData, fetchPage } = usePagination(fetchFn, { pageSize: 20 })
//   fetchFn 接收 (page) 并自行请求数据、返回后由 fetchFn 更新列表
export function usePagination(fetchFn, { pageSize = 20, initialPage = 1 } = {}) {
  const page = ref(initialPage)
  const total = ref(0)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

  async function fetchPage(target = page.value) {
    if (target < 1 || (total.value > 0 && target > totalPages.value)) return
    page.value = target
    await fetchFn(page.value)
  }

  function setTotal(t) {
    total.value = t
  }

  function goPage(p) {
    if (p < 1 || p > totalPages.value || p === page.value) return
    return fetchPage(p)
  }

  function next() {
    return goPage(page.value + 1)
  }

  function prev() {
    return goPage(page.value - 1)
  }

  function reset() {
    return fetchPage(1)
  }

  return { page, total, totalPages, setTotal, fetchPage, goPage, next, prev, reset }
}
