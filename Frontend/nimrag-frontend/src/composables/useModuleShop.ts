import { ref } from 'vue';

/**
 * Composable für Shop-Management
 * Verantwortung: Verwaltung des Shop-Status und Widget-Hinzufügen
 * Trennt Shop-Logik von der Hauptkomponente
 */
export function useModuleShop() {
  const isShopOpen = ref(false);

  /**
   * Toggled den Shop-Status (öffnen/schließen)
   */
  const toggleShop = () => {
    isShopOpen.value = !isShopOpen.value;
  };

  /**
   * Öffnet den Shop
   */
  const openShop = () => {
    isShopOpen.value = true;
  };

  /**
   * Schließt den Shop
   */
  const closeShop = () => {
    isShopOpen.value = false;
  };

  /**
   * Verarbeitet das Hinzufügen eines Widgets
   * @param cellId - ID der Zelle
   * @param component - Vue-Komponente des Widgets
   * @param insertCallback - Callback-Funktion zum Einfügen des Widgets
   */
  const addWidget = (
    cellId: number,
    component: any,
    insertCallback: (cellId: number, component: any) => void
  ) => {
    insertCallback(cellId, component);
    console.log('Widget zu Zelle hinzugefügt:', cellId);
  };

  return {
    isShopOpen,
    toggleShop,
    openShop,
    closeShop,
    addWidget,
  };
}

