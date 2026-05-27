import { ref, onMounted, onBeforeUnmount } from 'vue';

/**
 * Composable für Edit-Modus und Keyboard-Events
 * Verantwortung: Verwaltung des Edit-Modus und Keyboard-Navigation
 * Trennt UI-Interaktionen und macht Events wiederverwendbar und testbar
 */
export function useEditMode() {
  const isEditMode = ref(false);

  const setEditMode = (value: boolean) => {
    isEditMode.value = value;
  };

  /**
   * Toggled den Edit-Modus
   */
  const toggleEditMode = () => {
    setEditMode(!isEditMode.value);
  };

  /**
   * Verarbeitet Keyboard-Events
   * @param event - KeyboardEvent
   * @param callbacks - Objekt mit Callback-Funktionen für verschiedene Events
   */
  const handleKeydown = (
    event: KeyboardEvent,
    callbacks: {
      onShopToggle: () => void;
      onShopNavigate: (key: string) => void;
      onEditModeToggle?: () => void;
      onClockToggle?: () => void;
    }
  ) => {
    if (event.key === 'e' || event.key === 'E') {
      // E zum Öffnen/Schließen des Shops
      callbacks.onShopToggle();
    } else if (event.key === 'f' || event.key === 'F') {
      // F für Edit-Modus
      toggleEditMode();
      callbacks.onEditModeToggle?.();
    } else if (event.key === 'a' || event.key === 'A') {
      // A zum Umschalten der Uhr
      callbacks.onClockToggle?.();
    } else if (event.key === 'Escape') {
      // Escape zum Schließen des Shops
      callbacks.onShopToggle();
    } else {
      // Andere Keys (z.B. Arrow Keys für Shop-Navigation)
      callbacks.onShopNavigate(event.key);
    }
  };

  /**
   * Registriert den Keyboard-Listener mit Lifecycle-Hooks
   * @param callbacks - Callback-Funktionen
   */
  const setupKeyboardListener = (callbacks: {
    onShopToggle: () => void;
    onShopNavigate: (key: string) => void;
    onEditModeToggle?: () => void;
    onClockToggle?: () => void;
  }) => {
    const listener = (event: KeyboardEvent) => handleKeydown(event, callbacks);

    onMounted(() => {
      window.addEventListener('keydown', listener);
    });

    onBeforeUnmount(() => {
      window.removeEventListener('keydown', listener);
    });
  };

  return {
    isEditMode,
    setEditMode,
    toggleEditMode,
    setupKeyboardListener,
  };
}

