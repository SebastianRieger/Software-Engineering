<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const DUCK = 'https://media1.tenor.com/m/QuB7ztzrijgAAAAC/duck-spin.gif'

const gifs = [
  'https://media1.tenor.com/m/-dL_f8KjIfsAAAAd/monkey-meme.gif',
  'https://media1.tenor.com/m/wCrZqAL1cWMAAAAC/spinning-fish.gif',
  'https://media1.tenor.com/m/RPXO08OJgpMAAAAC/kermit-spinning.gif',
  'https://media1.tenor.com/m/WzWaEoFs9SgAAAAd/sea-lion-sea.gif',
  'https://media1.tenor.com/m/kDFIeIFtNygAAAAC/catspin.gif',
  'https://media1.tenor.com/m/_SdhAkuqUzMAAAAd/happy-gorilla.gif',
  'https://media1.tenor.com/m/t5fpt8VevjoAAAAC/chair-spin-spin-chair.gif',
  'https://media1.tenor.com/m/8VuZc8I8f7EAAAAC/oiia-cat.gif',
  'https://media1.tenor.com/m/ryculA0NQ1YAAAAC/capybara-horizontal.gif',
  DUCK,
  'https://media1.tenor.com/m/pHsc-VB8NccAAAAC/horse-horses.gif',
  'https://media1.tenor.com/m/NnRKrKp-mysAAAAC/spinning-chicken-chicken.gif',
  'https://media1.tenor.com/m/qFgG7AXlgSwAAAAC/spinning-chips.gif',
]

const currentGif = ref('')
const fit = computed(() => currentGif.value === DUCK ? 'object-contain' : 'object-cover')
let timer: ReturnType<typeof setInterval> | undefined

function pickRandom() {
  let next: string
  do { next = gifs[Math.floor(Math.random() * gifs.length)]! }
  while (next === currentGif.value)
  currentGif.value = next
}

onMounted(() => {
  pickRandom()
  timer = setInterval(pickRandom, 10_000)
})

onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="w-full h-full overflow-hidden">
    <img :src="currentGif" alt="" class="w-full h-full" :class="fit" />
  </div>
</template>
