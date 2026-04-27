<template>
  <div id="app">
    <!-- Jetons GLPI : backend FastAPI ; accès réservé intranet -->
    <DashboardPage />
  </div>
</template>

<script setup>
import DashboardPage from './components/DashboardPage.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: var(--app-bg);
  color: var(--app-text);
  transition: background-color 0.2s ease, color 0.2s ease;
}

#app {
  width: 100%;
  min-height: 100vh;
}
</style>
