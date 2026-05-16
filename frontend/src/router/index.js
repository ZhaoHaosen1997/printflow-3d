import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/sales' },
  { path: '/sales', name: 'Sales', component: () => import('../views/Sales.vue') },
  { path: '/colors', name: 'Colors', component: () => import('../views/Colors.vue') },
  { path: '/filaments', name: 'Filaments', component: () => import('../views/Filaments.vue') },
  { path: '/products', name: 'Products', component: () => import('../views/Products.vue') },
  { path: '/orders', name: 'Orders', component: () => import('../views/Orders.vue') },
  { path: '/paste-import', name: 'PasteImport', component: () => import('../views/PasteImport.vue') },
  { path: '/inventories', name: 'Inventories', component: () => import('../views/Inventories.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue') },
  { path: '/logs', name: 'LogViewer', component: () => import('../views/LogViewer.vue') },
  { path: '/print-tasks', name: 'PrintTasks', component: () => import('../views/PrintTasks.vue') },
  { path: '/buyers', name: 'Buyers', component: () => import('../views/Buyers.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
