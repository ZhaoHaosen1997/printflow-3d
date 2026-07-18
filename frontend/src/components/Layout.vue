<script setup>
import { ref, watch } from 'vue'
import { Menu, X } from '@lucide/vue'
import { useRoute } from 'vue-router'
import { useBreakpoint } from '../composables/useBreakpoint'
import Sidebar from './Sidebar.vue'

const route = useRoute()
const { isMobile } = useBreakpoint()
const sidebarOpen = ref(false)

watch(route, () => {
  sidebarOpen.value = false
})
</script>

<template>
  <div class="min-h-screen bg-dark flex flex-col md:flex-row">
    <!-- Mobile top bar -->
    <header
      v-if="isMobile"
      class="h-12 flex items-center justify-between px-3 bg-dark-card border-b border-border-inner flex-shrink-0"
    >
      <button
        class="p-2 -ml-1 text-gray-400 hover:text-gray-200"
        @click="sidebarOpen = !sidebarOpen"
      >
        <Menu class="w-5 h-5" />
      </button>
      <h1 class="text-sm font-serif text-gold-title">PrintFlow 3D</h1>
      <div class="w-9"></div>
    </header>

    <!-- Sidebar -->
    <Sidebar
      :mobile-open="isMobile && sidebarOpen"
      @close="sidebarOpen = false"
    />

    <!-- Main content -->
    <main class="flex-1 p-4 md:p-6 overflow-auto">
      <slot />
    </main>
  </div>
</template>
