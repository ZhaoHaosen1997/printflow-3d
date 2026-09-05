// 订单状态映射 —— 镜像自 backend/constants.py 的 ORDER_STATUS（修改须两端同步）
// 此前 StatusBadge/Buyers/PrintTasks/PasteImport/Orders 各自维护一份副本

export const ORDER_STATUS = {
  pending_ship: '待发货',
  shipped: '已发货',
  completed: '交易成功',
  cancelled: '已取消',
  returned: '退货',
  archived: '已归档',
}

// 订单来源映射（原 Orders.vue 内联对象）
export const SOURCE_LABELS = {
  paste_import: '粘贴导入',
  manual: '手动',
  wechat: '微信',
  migrated: '旧版导入',
  image_import: '识图导入',
}

// 打印任务状态（原 PrintTasks.vue statusConfig 的 label 部分）
export const TASK_STATUS = {
  pending: '待处理',
  printing: '打印中',
  done: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

export function orderStatusLabel(key) {
  return ORDER_STATUS[key] || key || '-'
}
