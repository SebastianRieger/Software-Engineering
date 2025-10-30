import { ref, onMounted, onUnmounted, type Ref } from 'vue';
import type { Widget, WidgetConfig } from '../types';
import { ApiService } from '../services/api.service';
import { WebSocketService } from '../services/websocket.service';

export function useWidget(widgetId: string) {
    const widget: Ref<Widget | null> = ref(null);
    const isLoading = ref(false);
    const error = ref<Error | null>(null);
    const apiService = ApiService.getInstance();
    const wsService = WebSocketService.getInstance();

    // store WS handler reference for removal on unmount
    let wsHandler: ((data: any) => void) | null = null;

    const fetchWidgetData = async () => {
        if (!widget.value) return;
        
        isLoading.value = true;
        error.value = null;

        try {
            const data = await apiService.get<any>(`/api/widgets/${widgetId}/data`);
            widget.value.data = data;
        } catch (err) {
            error.value = err instanceof Error ? err : new Error('Failed to fetch widget data');
        } finally {
            isLoading.value = false;
        }
    };

    const updateWidget = async (config: Partial<WidgetConfig>) => {
        if (!widget.value) return;

        try {
            const updatedWidget = await apiService.put<Widget>(
                `/api/widgets/${widgetId}`,
                { config }
            );
            widget.value = updatedWidget;
        } catch (err) {
            error.value = err instanceof Error ? err : new Error('Failed to update widget');
            throw error.value;
        }
    };

    const setupWebSocket = () => {
        wsHandler = (data: any) => {
            if (widget.value) {
                widget.value.data = data;
            }
        };
        wsService.on(`widget:${widgetId}:update`, wsHandler);
    };

    const cleanupWebSocket = () => {
        if (wsHandler) {
            wsService.off(`widget:${widgetId}:update`, wsHandler);
            wsHandler = null;
        }
    };

    onMounted(async () => {
        try {
            // Laden der Widget-Konfiguration
            const widgetData = await apiService.get<Widget>(`/api/widgets/${widgetId}`);
            widget.value = widgetData;

            // Initialer Datenabruf
            await fetchWidgetData();

            // WebSocket Setup
            setupWebSocket();
        } catch (err) {
            error.value = err instanceof Error ? err : new Error('Failed to initialize widget');
        }
    });

    onUnmounted(() => {
        cleanupWebSocket();
    });

    return {
        widget,
        isLoading,
        error,
        fetchWidgetData,
        updateWidget
    };
}