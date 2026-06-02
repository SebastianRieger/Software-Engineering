<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { Ref } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize.ts'
import { useFrageDesTages } from '../../composables/useFrageDesTages.ts'

const cellId     = inject<number>('cellId', 0)
const cellSizes  = inject<Ref<Record<number, CellSize>>>('cellSizes', ref({}))
const isEditMode = inject<Ref<boolean>>('isEditMode', ref(false))

const size = computed(() => {
  switch (cellSizes.value[cellId]) {
    case 4:  return 'large'
    case 2:  return 'medium'
    default: return 'small'
  }
})

const { question, isLoading, error, isRevealed, reveal } = useFrageDesTages()

const difficultyLabel: Record<string, string> = {
  easy:   'Leicht',
  medium: 'Mittel',
  hard:   'Schwer',
}
</script>

<template>
  <div class="fdq-widget" :class="`fdq-widget--${size}`">

    <!-- Header -->
    <header class="fdq-header">
      <span class="fdq-logo">Question of the Day</span>
      <span v-if="isLoading" class="fdq-status fdq-status--loading"><span class="fdq-dot" /></span>
      <span v-else-if="error" class="fdq-status fdq-status--error" :title="error">!</span>
      <span
        v-else-if="question"
        class="fdq-difficulty"
        :class="`fdq-difficulty--${question.difficulty}`"
      >{{ difficultyLabel[question.difficulty] ?? question.difficulty }}</span>
    </header>

    <!-- Systemzustände -->
    <div v-if="error"     class="fdq-empty">Frage nicht verfügbar</div>
    <div v-else-if="isLoading" class="fdq-empty">Lädt…</div>
    <div v-else-if="!question" class="fdq-empty">Keine Frage</div>

    <!-- Inhalt -->
    <div v-else class="fdq-content">

      <!-- SMALL: Nur Frage -->
      <template v-if="size === 'small'">
        <p class="fdq-question fdq-question--small">{{ question.question }}</p>
      </template>

      <!-- MEDIUM / LARGE: Kategorie + Frage + Antworten -->
      <template v-else>
        <p class="fdq-category">{{ question.category }}</p>

        <p class="fdq-question">{{ question.question }}</p>

        <ul class="fdq-answers">
          <li
            v-for="(answer, index) in question.answers"
            :key="index"
            class="fdq-answer"
            :class="{
              'fdq-answer--correct': isRevealed && answer === question.correct_answer,
              'fdq-answer--wrong':   isRevealed && answer !== question.correct_answer,
            }"
          >
            <span class="fdq-answer-letter">{{ String.fromCharCode(65 + index) }}</span>
            <span class="fdq-answer-text">{{ answer }}</span>
          </li>
        </ul>

        <!-- Reveal-Button: nur im Edit-Modus, solange Antwort nicht aufgedeckt -->
        <button
          v-if="isEditMode && !isRevealed"
          class="fdq-reveal-btn"
          @click="reveal()"
        >
          Antwort aufdecken
        </button>
      </template>

    </div>
  </div>
</template>

<style scoped>
/* ── Variablen & Container ─────────────────────────── */
.fdq-widget {
  --c-bg:       #111;
  --c-surface:  #1a1a1a;
  --c-border:   rgba(255, 255, 255, 0.07);
  --c-text:     #e8e8e8;
  --c-muted:    #666;
  --c-category: #999;
  --c-correct:  #27ae60;
  --c-wrong:    rgba(255, 255, 255, 0.18);
  --c-accent:   #4a9eff;
  --font-head:  'Georgia', 'Times New Roman', serif;
  --font-ui:    'DM Mono', 'Courier New', monospace;

  width: 100%;
  height: 100%;
  background: var(--c-bg);
  color: var(--c-text);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  font-family: var(--font-head);
  user-select: none;
}

/* ── Header ────────────────────────────────────────── */
.fdq-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.fdq-logo {
  font-family: var(--font-ui);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #fff;
  opacity: 0.9;
}

.fdq-status {
  font-family: var(--font-ui);
  font-size: 10px;
  color: var(--c-muted);
}

.fdq-status--error { color: #c0392b; font-weight: 700; }

.fdq-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: var(--c-muted);
  border-radius: 50%;
  animation: fdq-pulse 1.4s ease-in-out infinite;
}

@keyframes fdq-pulse {
  0%, 100% { opacity: 0.3; }
  50%       { opacity: 1;   }
}

/* ── Schwierigkeit ─────────────────────────────────── */
.fdq-difficulty {
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--c-border);
  color: var(--c-muted);
}

.fdq-difficulty--easy   { color: #27ae60; border-color: rgba(39, 174, 96, 0.35); }
.fdq-difficulty--medium { color: #e67e22; border-color: rgba(230, 126, 34, 0.35); }
.fdq-difficulty--hard   { color: #c0392b; border-color: rgba(192, 57, 43, 0.35); }

/* ── Leer / Fehler ─────────────────────────────────── */
.fdq-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--c-muted);
  letter-spacing: 0.08em;
}

/* ── Inhalt ────────────────────────────────────────── */
.fdq-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  padding: 8px 10px 10px;
  gap: 6px;
}

/* ── Kategorie ─────────────────────────────────────── */
.fdq-category {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 8px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--c-category);
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Frage ─────────────────────────────────────────── */
.fdq-question {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
  color: var(--c-text);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex-shrink: 0;
}

.fdq-question--small {
  flex: 1;
  font-size: 15px;
  -webkit-line-clamp: 6;
  display: -webkit-box;
}

.fdq-widget--large .fdq-question {
  font-size: 14px;
  -webkit-line-clamp: 3;
}

/* ── Antworten ─────────────────────────────────────── */
.fdq-answers {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.fdq-widget--medium .fdq-answers {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 4px;
}

.fdq-answer {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  padding: 5px 8px;
  border-radius: 4px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  transition: background 0.25s ease, border-color 0.25s ease, opacity 0.25s ease;
  overflow: hidden;
  min-height: 0;
  flex-shrink: 0;
}

.fdq-answer--correct {
  background: rgba(39, 174, 96, 0.15);
  border-color: rgba(39, 174, 96, 0.55);
}

.fdq-answer--wrong {
  opacity: 0.35;
}

.fdq-answer-letter {
  font-family: var(--font-ui);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--c-muted);
  flex-shrink: 0;
  width: 12px;
  padding-top: 1px;
}

.fdq-answer--correct .fdq-answer-letter {
  color: #27ae60;
}

.fdq-answer-text {
  font-size: 10px;
  line-height: 1.35;
  color: var(--c-text);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.fdq-widget--large .fdq-answer {
  padding: 7px 10px;
}

.fdq-widget--large .fdq-answer-text {
  font-size: 11px;
}

/* ── Reveal-Button ─────────────────────────────────── */
.fdq-reveal-btn {
  flex-shrink: 0;
  margin-top: auto;
  padding: 6px 14px;
  background: rgba(74, 158, 255, 0.15);
  border: 1px solid rgba(74, 158, 255, 0.45);
  border-radius: 5px;
  color: var(--c-accent);
  font-family: var(--font-ui);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.12s ease;
  align-self: stretch;
}

.fdq-reveal-btn:hover {
  background: rgba(74, 158, 255, 0.28);
  border-color: rgba(74, 158, 255, 0.75);
}

.fdq-reveal-btn:active {
  transform: scale(0.97);
}
</style>
