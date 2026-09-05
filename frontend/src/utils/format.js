// 全站共享的格式化函数（此前在 Dashboard/Sales/Buyers/ArchivedData 各自复制）

export function formatMoney(val, { dash = true } = {}) {
  if (val == null || val === '') return dash ? '-' : '¥0.00'
  return `¥${Number(val).toFixed(2)}`
}

export function formatDateTime(val) {
  if (!val) return '-'
  if (typeof val !== 'string') return '-'
  return val.slice(0, 16).replace('T', ' ')
}

// 商品/订单分类中文映射（与后端 categories 种子数据保持一致）
const CATEGORY_LABELS = {
  counter: '计数器',
  token: '指示物',
  other: '其他',
  bundle: '合集',
}

export function formatCategory(val) {
  return CATEGORY_LABELS[val] || val || '-'
}
