import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
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
  { path: '/archived', name: 'ArchivedData', component: () => import('../views/ArchivedData.vue') },
  { path: '/poster-generator', name: 'PosterGenerator', component: () => import('../views/PosterGenerator.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
