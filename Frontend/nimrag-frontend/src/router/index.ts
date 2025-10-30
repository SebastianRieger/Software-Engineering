import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/widgets',
    name: 'Widgets',
    component: () => import('../views/Widgets.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Simple auth guard example (can be replaced with real store-based guard)
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('auth_token')
  // Protect /widgets as an example
  if (to.path.startsWith('/widgets') && !token) {
    return next({ name: 'Home' })
  }
  next()
})

export default router
