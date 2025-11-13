<script setup lang="ts">
import { ref, onMounted } from 'vue'

const modules = import.meta.glob("../widgets/*.vue")
const moduleList = ref<Array<{ name: string, path: string, component: any }>>([])

onMounted(async () => {
  // Durchlaufe alle Module
  for (const path in modules) {
    // Extrahiere den Dateinamen ohne Pfad und Extension
    const fileName = path.split('/').pop()?.replace('.vue', '') || ''
    
    // Lade die Komponente (lazy load)
    const moduleLoader = modules[path]
    if (moduleLoader) {
      const module = await moduleLoader() as any
      
      moduleList.value.push({
        name: fileName,
        path: path,
        component: module.default
      })
    }
  }

})
</script>

<script lang="ts">
//startet nicht beim init der seite -> eigene Funktionen und so hier rein
</script>

<template>
  <div class="w-full h-full card flex flex-col justify-center">
    <h3>Verfügbare Module</h3>
    <ul>
      <li v-for="mod in moduleList" :key="mod.path" class="module-item">
        <strong>{{ mod.name }}</strong>
        <!-- Dynamisch die Komponente rendern -->
        <component :is="mod.component" />
      </li>
    </ul>
  </div>
</template>

<style scoped>
.card { background:#111; color:#eee; padding:16px; }
.module-item {
  margin-bottom: 16px;
  padding: 8px;
  border: 1px solid #333;
}
</style>