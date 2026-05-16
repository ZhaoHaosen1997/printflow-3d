<script setup>
defineProps({
  status: { type: String, required: true },
  size: { type: String, default: 'sm' },
})

const statusMap = {
  active:       { cls: 'badge-success', label: '启用' },
  standard:     { cls: 'badge-info',    label: '标准色' },
  combo:        { cls: 'badge-accent',  label: '组合色' },
  archived:     { cls: 'badge-neutral', label: '已归档' },
  inactive:     { cls: 'badge-neutral', label: '停用' },
  // Order statuses (Chinese — new)
  '待发货':     { cls: 'badge-warning', label: '待发货' },
  '已发货':     { cls: 'badge-info',    label: '已发货' },
  '交易成功':   { cls: 'badge-success', label: '交易成功' },
  '已取消':     { cls: 'badge-danger',  label: '已取消' },
  '退货':       { cls: 'badge-danger',  label: '退货' },
  '已归档':     { cls: 'badge-neutral', label: '已归档' },
  // Order statuses (English — compat with old data)
  pending:      { cls: 'badge-warning', label: '待发货' },
  shipped:      { cls: 'badge-info',    label: '已发货' },
  completed:    { cls: 'badge-success', label: '交易成功' },
  cancelled:    { cls: 'badge-danger',  label: '已取消' },
  // Product categories
  bundle:       { cls: 'badge-purple',  label: '合集' },
  counter:      { cls: 'badge-info',    label: '计数器' },
  token:        { cls: 'badge-success', label: '指示物' },
  other:        { cls: 'badge-warning', label: '其他' },
}
</script>

<template>
  <span
    :class="[
      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap',
      (statusMap[status] || statusMap.other).cls,
    ]"
  >
    {{ (statusMap[status] || { label: status }).label }}
  </span>
</template>

<style scoped>
.badge-success,
.badge-info,
.badge-warning,
.badge-danger,
.badge-purple,
.badge-neutral,
.badge-accent { display: inline-flex; }

.badge-success { background: var(--badge-success-bg); color: var(--badge-success-text); }
.badge-info    { background: var(--badge-info-bg);    color: var(--badge-info-text); }
.badge-warning { background: var(--badge-warning-bg); color: var(--badge-warning-text); }
.badge-danger  { background: var(--badge-danger-bg);  color: var(--badge-danger-text); }
.badge-purple  { background: var(--badge-purple-bg);  color: var(--badge-purple-text); }
.badge-neutral { background: var(--badge-neutral-bg); color: var(--badge-neutral-text); }
.badge-accent  { background: color-mix(in srgb, var(--app-accent) 15%, transparent); color: var(--app-accent); }
</style>
