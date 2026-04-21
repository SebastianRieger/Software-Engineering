import { createApp } from 'vue';

interface WidgetApp {
  unmount: () => void;
}

/**
 * Composable für Widget-Management
 * Verantwortung: Verwaltung von aktiven Widgets, Einfügen, Löschen und Verschieben
 * Trennt DOM-Manipulation und Zustand von der UI-Komponente
 */
export function useWidgetManager() {
  const activeWidgets: { [key: number]: WidgetApp } = {};

  /**
   * Einfügen eines Widgets in eine Zelle
   * @param cellId - ID der Zelle
   * @param widgetComponent - Vue-Komponente des Widgets
   */
  const insertWidgetIntoCell = (cellId: number, widgetComponent: any) => {
    const mount = document.getElementById(`cell-content-${cellId}`);
    if (!mount) {
      console.error(`Mount für Zelle ${cellId} nicht gefunden`);
      return;
    }

    // Cleanup alter Widgets
    if (activeWidgets[cellId]) {
      activeWidgets[cellId].unmount();
    }

    // Container leeren und neu erstellen
    mount.innerHTML = '';
    const widgetContainer = document.createElement('div');
    widgetContainer.className = 'w-full h-full';
    mount.appendChild(widgetContainer);

    // Vue-App erstellen und mounten
    const app = createApp(widgetComponent);
    app.mount(widgetContainer);
    activeWidgets[cellId] = app;
  };

  /**
   * Zelle leeren und Platzhalter wiederherstellen
   * @param cellId - ID der Zelle
   */
  const clearCell = (cellId: number) => {
    const mount = document.getElementById(`cell-content-${cellId}`);
    if (!mount) {
      return;
    }

    // Vue-App unmounten und löschen
    if (activeWidgets[cellId]) {
      activeWidgets[cellId].unmount();
      delete activeWidgets[cellId];
    }

    // Platzhalter wiederherstellen
    mount.innerHTML = `
      <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
        ${String(cellId).padStart(2, '0')}
      </div>
    `;
  };

  /**
   * Widgets verschieben (z.B. durch Drag & Drop)
   * @param sourceCellId - Quellzelle
   * @param targetCellId - Zielzelle
   */
  const moveWidgets = ({
    sourceCellId,
    targetCellId,
  }: {
    sourceCellId: number;
    targetCellId: number;
  }) => {
    const sourceApp = activeWidgets[sourceCellId];
    const targetApp = activeWidgets[targetCellId];

    if (sourceApp && targetApp) {
      // Beide haben Widgets: vertauschen
      activeWidgets[targetCellId] = sourceApp;
      activeWidgets[sourceCellId] = targetApp;
    } else if (sourceApp && !targetApp) {
      // Nur Quelle hat Widget: verschieben
      activeWidgets[targetCellId] = sourceApp;
      delete activeWidgets[sourceCellId];
    } else if (!sourceApp && targetApp) {
      // Nur Ziel hat Widget: verschieben
      activeWidgets[sourceCellId] = targetApp;
      delete activeWidgets[targetCellId];
    }
  };

  return {
    activeWidgets,
    insertWidgetIntoCell,
    clearCell,
    moveWidgets,
  };
}

