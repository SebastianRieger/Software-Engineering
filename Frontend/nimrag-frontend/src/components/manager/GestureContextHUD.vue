<script setup lang="ts">
import { computed } from 'vue'
import type { UIActionType } from '../../types/interactions'

type HudContext =
  | 'idle'
  | 'edit-empty-focused'
  | 'edit-widget-focused'
  | 'dragging'
  | 'delete-confirm'
  | 'shop'

type GestureIcon = 'circle' | 'push-short' | 'push-long' | 'browse' | 'resize' | 'grab' | 'pinch-close' | 'pinch-open'

interface Hint {
  icon: GestureIcon
  label: string
  action: UIActionType
}

const props = defineProps<{
  isEditMode: boolean
  isShopOpen: boolean
  isDragging: boolean
  deleteConfirmPending: boolean
  focusedCellIsEmpty: boolean
}>()

const emit = defineEmits<{
  (e: 'action-clicked', action: UIActionType): void
}>()

const context = computed<HudContext>(() => {
  if (props.isShopOpen) return 'shop'
  if (props.isDragging) return 'dragging'
  if (props.deleteConfirmPending) return 'delete-confirm'
  if (!props.isEditMode) return 'idle'
  if (props.focusedCellIsEmpty) return 'edit-empty-focused'
  return 'edit-widget-focused'
})

const hints = computed<Hint[]>(() => {
  switch (context.value) {
    case 'idle':
      return [
        { icon: 'circle',      label: 'Edit starten',  action: 'toggle_edit_mode' },
      ]
    case 'edit-empty-focused':
      return [
        { icon: 'pinch-close', label: 'Shop öffnen',   action: 'primary_click' },
        { icon: 'push-short',  label: 'Skalieren',      action: 'resize_expand' },
        { icon: 'circle',      label: 'Beenden',        action: 'toggle_edit_mode' },
      ]
    case 'edit-widget-focused':
      return [
        { icon: 'pinch-close', label: 'Greifen',        action: 'primary_click' },
        { icon: 'push-long',   label: 'Löschen',        action: 'delete_widget' },
        { icon: 'push-short',  label: 'Skalieren',      action: 'resize_expand' },
        { icon: 'circle',      label: 'Beenden',        action: 'toggle_edit_mode' },
      ]
    case 'dragging':
      return [
        { icon: 'pinch-open',  label: 'Ablegen',        action: 'drop_widget' },
        { icon: 'circle',      label: 'Abbrechen',      action: 'toggle_edit_mode' },
      ]
    case 'delete-confirm':
      return [
        { icon: 'push-long',   label: 'Jetzt löschen',  action: 'delete_widget' },
        { icon: 'circle',      label: 'Abbrechen',      action: 'toggle_edit_mode' },
      ]
    case 'shop':
      return [
        { icon: 'browse',      label: 'Nächstes',       action: 'move_focus_right' },
        { icon: 'pinch-close', label: 'Hinzufügen',     action: 'confirm_selection' },
        { icon: 'circle',      label: 'Schließen',      action: 'toggle_edit_mode' },
      ]
  }
})

const alwaysVisible = computed(() => context.value === 'idle')

function handleHintClick(action: UIActionType): void {
  emit('action-clicked', action)
}
</script>

<template>
  <Transition name="hud-slide">
    <div
      v-if="isEditMode || isShopOpen || alwaysVisible"
      class="gesture-hud"
      :class="{ 'gesture-hud--idle': alwaysVisible }"
      role="status"
      aria-live="polite"
    >
      <TransitionGroup name="chip-swap" tag="div" class="hud-chips">
        <button
          v-for="hint in hints"
          :key="hint.icon + hint.label"
          type="button"
          class="hint-chip"
          @click="handleHintClick(hint.action)"
        >

          <!-- ── Animated gesture icon ── -->
          <div class="gesture-icon" aria-hidden="true">

            <!-- Circle gesture: rotating arc segment -->
            <svg v-if="hint.icon === 'circle'" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="7" stroke="rgba(255,255,255,0.15)" stroke-width="1.5"/>
              <circle
                cx="10" cy="10" r="7"
                stroke="white" stroke-width="1.5"
                stroke-dasharray="26 18"
                stroke-linecap="round"
                class="anim-circle-spin"
              />
            </svg>

            <!-- Push short: chevron that pulses forward -->
            <svg v-else-if="hint.icon === 'push-short'" viewBox="0 0 20 20" fill="none">
              <polyline
                points="6,5 14,10 6,15"
                stroke="rgba(255,255,255,0.28)" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"
              />
              <polyline
                points="6,5 14,10 6,15"
                stroke="white" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"
                class="anim-push-fwd"
              />
            </svg>

            <!-- Push long: progress ring (hold indicator) -->
            <svg v-else-if="hint.icon === 'push-long'" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="6.5" stroke="rgba(255,255,255,0.14)" stroke-width="1.5"/>
              <circle
                cx="10" cy="10" r="6.5"
                stroke="white" stroke-width="1.5"
                stroke-dasharray="41" stroke-dashoffset="41"
                stroke-linecap="round"
                class="anim-fill-ring"
              />
              <circle cx="10" cy="10" r="2" fill="rgba(255,255,255,0.5)" class="anim-center-dot"/>
            </svg>

            <!-- Browse: left / right arrows alternating -->
            <svg v-else-if="hint.icon === 'browse'" viewBox="0 0 20 20" fill="none">
              <polyline
                points="9,6 5,10 9,14"
                stroke="white" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"
                class="anim-browse-left"
              />
              <polyline
                points="11,6 15,10 11,14"
                stroke="white" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"
                class="anim-browse-right"
              />
            </svg>

            <!-- Resize: 4 corner arrows expanding -->
            <svg v-else-if="hint.icon === 'resize'" viewBox="0 0 20 20" fill="none" class="anim-resize-group">
              <!-- top-left -->
              <path d="M3 7 L3 3 L7 3" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              <!-- top-right -->
              <path d="M17 7 L17 3 L13 3" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              <!-- bottom-left -->
              <path d="M3 13 L3 17 L7 17" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
              <!-- bottom-right -->
              <path d="M17 13 L17 17 L13 17" stroke="white" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>

            <!-- Pinch close: thumb + index converge -->
            <svg v-else-if="hint.icon === 'pinch-close'" viewBox="0 0 20 20" fill="none">
              <!-- thumb dot -->
              <circle cx="4" cy="10" r="2.2" fill="white" class="anim-pinch-thumb-close"/>
              <!-- index dot -->
              <circle cx="16" cy="10" r="2.2" fill="white" class="anim-pinch-index-close"/>
              <!-- center target -->
              <circle cx="10" cy="10" r="1.2" fill="rgba(255,255,255,0.4)" class="anim-pinch-center"/>
            </svg>

            <!-- Pinch open: thumb + index diverge -->
            <svg v-else-if="hint.icon === 'pinch-open'" viewBox="0 0 20 20" fill="none">
              <!-- thumb dot -->
              <circle cx="10" cy="10" r="2.2" fill="white" class="anim-pinch-thumb-open"/>
              <!-- index dot -->
              <circle cx="10" cy="10" r="2.2" fill="white" class="anim-pinch-index-open"/>
              <!-- spread indicator lines -->
              <line x1="4" y1="10" x2="7" y2="10" stroke="rgba(255,255,255,0.3)" stroke-width="1" stroke-linecap="round" class="anim-pinch-spread-line anim-pinch-spread-left"/>
              <line x1="13" y1="10" x2="16" y2="10" stroke="rgba(255,255,255,0.3)" stroke-width="1" stroke-linecap="round" class="anim-pinch-spread-line anim-pinch-spread-right"/>
            </svg>

            <!-- Grab: dot lifts up (widget pickup) -->
            <svg v-else-if="hint.icon === 'grab'" viewBox="0 0 20 20" fill="none">
              <!-- shadow/origin -->
              <ellipse cx="10" cy="15" rx="4" ry="1.5" fill="rgba(255,255,255,0.12)" class="anim-grab-shadow"/>
              <!-- widget box -->
              <rect x="6" y="9" width="8" height="6" rx="1.5"
                fill="rgba(255,255,255,0.0)" stroke="rgba(255,255,255,0.3)" stroke-width="1.2"
                class="anim-grab-box"
              />
              <!-- lifted widget -->
              <rect x="6" y="9" width="8" height="6" rx="1.5"
                fill="rgba(255,255,255,0.0)" stroke="white" stroke-width="1.2"
                class="anim-grab-lift"
              />
              <!-- hand lines (index + middle fingers) -->
              <line x1="8.5" y1="6" x2="8.5" y2="9.5" stroke="white" stroke-width="1.2" stroke-linecap="round" class="anim-finger" style="--delay:0s"/>
              <line x1="11.5" y1="5.5" x2="11.5" y2="9" stroke="white" stroke-width="1.2" stroke-linecap="round" class="anim-finger" style="--delay:0.08s"/>
            </svg>

          </div>

          <span class="hint-label">{{ hint.label }}</span>
        </button>
      </TransitionGroup>
    </div>
  </Transition>
</template>

<style scoped>
.gesture-hud {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1100;
}

.gesture-hud--idle {
  opacity: 0.55;
}

.hud-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.hint-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 9999px;
  padding: 6px 14px 6px 8px;
  cursor: pointer;
  transition: background 160ms ease, border-color 160ms ease;
  font-family: inherit;
  color: inherit;
  outline: none;
}

.hint-chip:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.24);
}

.hint-chip:active {
  background: rgba(255, 255, 255, 0.22);
}

.hint-chip:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

.gesture-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gesture-icon svg {
  width: 20px;
  height: 20px;
  overflow: visible;
}

.hint-label {
  font-size: 0.70rem;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.76);
  white-space: nowrap;
}

/* ─── Gesture animations ──────────────────────────────────────── */

/* Circle: arc segment rotates continuously */
.anim-circle-spin {
  transform-box: fill-box;
  transform-origin: center;
  animation: circle-spin 2.2s linear infinite;
}

@keyframes circle-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* Push short: chevron fades+slides forward, resets */
.anim-push-fwd {
  animation: push-fwd 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes push-fwd {
  0%   { transform: translateX(0);    opacity: 1; }
  35%  { transform: translateX(4px);  opacity: 0; }
  36%  { transform: translateX(-2px); opacity: 0; }
  55%  { transform: translateX(0);    opacity: 1; }
  100% { transform: translateX(0);    opacity: 1; }
}

/* Push long: ring draws itself slowly (hold) */
.anim-fill-ring {
  transform-box: fill-box;
  transform-origin: center;
  transform: rotate(-90deg);
  animation: fill-ring 2.4s ease-in-out infinite;
}

@keyframes fill-ring {
  0%   { stroke-dashoffset: 41; }
  65%  { stroke-dashoffset: 0; }
  85%  { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: 41; }
}

.anim-center-dot {
  animation: center-dot-pulse 2.4s ease-in-out infinite;
}

@keyframes center-dot-pulse {
  0%, 100% { opacity: 0.4; transform: scale(1);    transform-box: fill-box; transform-origin: center; }
  65%       { opacity: 1;   transform: scale(1.35); transform-box: fill-box; transform-origin: center; }
  85%       { opacity: 1;   transform: scale(1.35); transform-box: fill-box; transform-origin: center; }
}

/* Browse: left and right arrows alternate */
.anim-browse-left {
  animation: browse-left 2s ease-in-out infinite;
}

.anim-browse-right {
  animation: browse-right 2s ease-in-out infinite;
}

@keyframes browse-left {
  0%   { opacity: 1;   transform: translateX(0); }
  20%  { opacity: 1;   transform: translateX(-2px); }
  45%  { opacity: 0.2; transform: translateX(0); }
  100% { opacity: 0.2; transform: translateX(0); }
}

@keyframes browse-right {
  0%   { opacity: 0.2; transform: translateX(0); }
  50%  { opacity: 0.2; transform: translateX(0); }
  70%  { opacity: 1;   transform: translateX(2px); }
  90%  { opacity: 1;   transform: translateX(0); }
  100% { opacity: 0.2; transform: translateX(0); }
}

/* Resize: all 4 corner brackets pulse outward */
.anim-resize-group {
  animation: resize-expand 2s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}

@keyframes resize-expand {
  0%, 100% { transform: scale(0.88); opacity: 0.65; }
  45%, 55%  { transform: scale(1.14); opacity: 1; }
}

/* Grab: box lifts and fingers close */
.anim-grab-box {
  animation: grab-box 2s ease-in-out infinite;
}

@keyframes grab-box {
  0%, 100% { opacity: 0.3; transform: translateY(0); }
  40%       { opacity: 0.1; }
  50%, 80%  { opacity: 0;   transform: translateY(-4px); }
}

.anim-grab-lift {
  animation: grab-lift 2s ease-in-out infinite;
}

@keyframes grab-lift {
  0%, 30% { opacity: 0; transform: translateY(0); }
  50%, 80% { opacity: 1; transform: translateY(-4px); }
  100%     { opacity: 0; transform: translateY(-4px); }
}

.anim-grab-shadow {
  animation: grab-shadow 2s ease-in-out infinite;
}

@keyframes grab-shadow {
  0%, 35%  { opacity: 1;   transform: scale(1);    transform-box: fill-box; transform-origin: center; }
  55%, 80% { opacity: 0.3; transform: scale(0.5);  transform-box: fill-box; transform-origin: center; }
  100%     { opacity: 1;   transform: scale(1);    transform-box: fill-box; transform-origin: center; }
}

.anim-finger {
  animation: finger-close 2s ease-in-out infinite var(--delay, 0s);
}

@keyframes finger-close {
  0%, 25%  { transform: translateY(0);   opacity: 1; }
  45%, 85% { transform: translateY(3px); opacity: 0.6; }
  100%     { transform: translateY(0);   opacity: 1; }
}

/* ─── HUD slide in/out ──────────────────────────────────────────── */
.hud-slide-enter-active,
.hud-slide-leave-active {
  transition: transform 240ms cubic-bezier(0.4, 0, 0.2, 1), opacity 240ms ease;
}

.hud-slide-enter-from,
.hud-slide-leave-to {
  transform: translateX(-50%) translateY(12px);
  opacity: 0;
}

/* ─── Chip context swap ─────────────────────────────────────────── */
.chip-swap-enter-active,
.chip-swap-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.chip-swap-enter-from,
.chip-swap-leave-to {
  opacity: 0;
  transform: translateY(5px) scale(0.95);
}

.chip-swap-leave-active {
  position: absolute;
}

/* ─── Pinch close: two dots converge to center ──────────────────── */
.anim-pinch-thumb-close {
  animation: pinch-thumb-in 1.6s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}

.anim-pinch-index-close {
  animation: pinch-index-in 1.6s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}

.anim-pinch-center {
  animation: pinch-center-appear 1.6s ease-in-out infinite;
}

@keyframes pinch-thumb-in {
  0%, 20%  { transform: translateX(0);    opacity: 1; }
  55%, 75% { transform: translateX(5px);  opacity: 0.9; }
  85%, 100% { transform: translateX(0);   opacity: 0.6; }
}

@keyframes pinch-index-in {
  0%, 20%  { transform: translateX(0);    opacity: 1; }
  55%, 75% { transform: translateX(-5px); opacity: 0.9; }
  85%, 100% { transform: translateX(0);   opacity: 0.6; }
}

@keyframes pinch-center-appear {
  0%, 40%  { opacity: 0; transform: scale(0.5); transform-box: fill-box; transform-origin: center; }
  60%, 80% { opacity: 1; transform: scale(1.4); transform-box: fill-box; transform-origin: center; }
  100%     { opacity: 0; transform: scale(1);   transform-box: fill-box; transform-origin: center; }
}

/* ─── Pinch open: dots move apart from center ───────────────────── */
.anim-pinch-thumb-open {
  animation: pinch-thumb-out 1.6s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}

.anim-pinch-index-open {
  animation: pinch-index-out 1.6s ease-in-out infinite;
  transform-box: fill-box;
  transform-origin: center;
}

.anim-pinch-spread-line {
  animation: pinch-line-fade 1.6s ease-in-out infinite;
}

@keyframes pinch-thumb-out {
  0%, 20%  { transform: translateX(0);    opacity: 0.3; }
  55%, 75% { transform: translateX(-5px); opacity: 1; }
  85%, 100% { transform: translateX(0);   opacity: 0.3; }
}

@keyframes pinch-index-out {
  0%, 20%  { transform: translateX(0);    opacity: 0.3; }
  55%, 75% { transform: translateX(5px);  opacity: 1; }
  85%, 100% { transform: translateX(0);   opacity: 0.3; }
}

@keyframes pinch-line-fade {
  0%, 40%  { opacity: 0; }
  60%, 80% { opacity: 0.8; }
  100%     { opacity: 0; }
}

/* ─── Reduced motion ────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .anim-circle-spin,
  .anim-push-fwd,
  .anim-fill-ring,
  .anim-center-dot,
  .anim-browse-left,
  .anim-browse-right,
  .anim-resize-group,
  .anim-grab-box,
  .anim-grab-lift,
  .anim-grab-shadow,
  .anim-finger,
  .anim-pinch-thumb-close,
  .anim-pinch-index-close,
  .anim-pinch-center,
  .anim-pinch-thumb-open,
  .anim-pinch-index-open,
  .anim-pinch-spread-line {
    animation: none;
  }

  .hud-slide-enter-active,
  .hud-slide-leave-active,
  .chip-swap-enter-active,
  .chip-swap-leave-active {
    transition: none;
  }
}
</style>
