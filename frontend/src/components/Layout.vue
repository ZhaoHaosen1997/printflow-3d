<script setup>
import Sidebar from './Sidebar.vue'
</script>

<template>
  <div class="min-h-screen bg-dark flex">
    <Sidebar />
    <main class="flex-1 p-6 overflow-auto">
      <slot />
    </main>
  </div>
</template>
