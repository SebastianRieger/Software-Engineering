<template>
  <div id="app-root">
    <header class="app-header">
      <h1>Nimrag Smart Mirror</h1>
      <nav>
        <router-link to="/">Home</router-link>
        <router-link to="/widgets">Widgets</router-link>
      </nav>
    </header>

    <main>
      <router-view />
    </main>

    <footer class="app-footer">© Nimrag Project</footer>
  </div>
</template>

<script setup lang="ts">
// Root shell, minimal logic here. Keep App light-weight.
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
}

.app-header nav a {
  margin-left: 1rem;
}

main {
  padding: 1rem 2rem;
}

.app-footer {
  margin-top: 2rem;
  text-align: center;
  font-size: 0.9rem;
  color: rgba(255,255,255,0.6);
}
</style>

