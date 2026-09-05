// 数组工具：替代各页面复制的 indexOf/splice toggle 模式

export function toggleItem(arr, value) {
  const idx = arr.indexOf(value)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(value)
  return arr
}
