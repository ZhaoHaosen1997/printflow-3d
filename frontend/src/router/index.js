import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/colors' },
  { path: '/colors', name: 'Colors', component: () => import('../views/Colors.vue') },
  { path: '/filaments', name: 'Filaments', component: () => import('../views/Filaments.vue') },
  { path: '/products', name: 'Products', component: () => import('../views/Products.vue') },
  { path: '/orders', name: 'Orders', component: () => import('../views/Orders.vue') },
  { path: '/paste-import', name: 'PasteImport', component: () => import('../views/PasteImport.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
