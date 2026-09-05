<script setup>
import Layout from './components/Layout.vue'
import ToastContainer from './components/ToastContainer.vue'
</script>

<template>
  <Layout>
    <router-view />
  </Layout>
  <ToastContainer />
</template>
