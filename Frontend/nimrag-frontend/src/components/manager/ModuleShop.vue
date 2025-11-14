<script setup lang="ts">
import { ref, onMounted, defineEmits, defineExpose } from 'vue'

const emit = defineEmits(['addWidget'])
const modules = import.meta.glob("../widgets/*.vue")
const moduleList = ref<Array<{ name: string, path: string, component: any }>>([])
const currentIndex = ref(0)

// Function to add the current widget to a cell
const addCurrentWidgetToCell = (cellId: number) => {
  emit('addWidget', { cellId, component: moduleList.value[currentIndex.value].component })
}

// Carousel navigation
const nextModule = () => {
  if (currentIndex.value < moduleList.value.length - 1) {
    currentIndex.value++
  } else {
    currentIndex.value = 0
  }
}

const prevModule = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
  } else {
    currentIndex.value = moduleList.value.length - 1
  }
}

onMounted(async () => {
  // Load all modules
  for (const path in modules) {
    const fileName = path.split('/').pop()?.replace('.vue', '') || ''

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

// Expose methods to parent component
defineExpose({
  nextModule,
  prevModule
})
</script>

<template>
  <div class="module-shop">
    <h3 class="title">Widget Shop</h3>

    <div v-if="moduleList.length > 0" class="carousel">
      <!-- Carousel Navigation -->
      <button @click="prevModule" class="nav-btn prev-btn"><</button>

      <!-- Current Module Preview -->
      <div class="module-preview">
        <h4>{{ moduleList[currentIndex].name }}</h4>
        <div class="preview-container">
          <component :is="moduleList[currentIndex].component" />
        </div>

        <!-- Quick Cell Selection -->
        <div class="cell-selection">
          <p>Add to cell:</p>
          <div class="cell-buttons">
            <button
                v-for="cellId in [1, 2, 3, 4, 5, 6, 7, 8, 9]"
                :key="cellId"
                @click="addCurrentWidgetToCell(cellId)"
                class="cell-btn"
            >
              {{ cellId }}
            </button>
          </div>
        </div>
      </div>

      <button @click="nextModule" class="nav-btn next-btn">></button>
    </div>

    <div v-else class="loading">
      Loading modules...
    </div>
  </div>
</template>

<style scoped>
.module-shop {
  background: #222;
  color: #eee;
  padding: 20px;
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
}

.title {
  text-align: center;
  margin-bottom: 16px;
  font-size: 1.5rem;
}

.carousel {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.module-preview {
  flex: 1;
  text-align: center;
}

.preview-container {
  background: #111;
  border-radius: 8px;
  padding: 16px;
  margin: 10px 0;
  max-height: 200px;
  overflow: hidden;
}

.nav-btn {
  background: #444;
  color: white;
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  font-size: 18px;
  cursor: pointer;
  margin: 0 10px;
}

.nav-btn:hover {
  background: #555;
}

.cell-selection {
  margin-top: 16px;
}

.cell-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
}

.cell-btn {
  background: #444;
  color: white;
  border: none;
  border-radius: 4px;
  width: 36px;
  height: 36px;
  cursor: pointer;
}

.cell-btn:hover {
  background: #555;
}
</style>