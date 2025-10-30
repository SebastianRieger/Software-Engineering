import { ref, type Ref } from 'vue';

export interface WebSocketMessage {
    event: string;
    data: any;
    timestamp: number;
}

export class WebSocketService {
    private static instance: WebSocketService;
    private socket: WebSocket | null = null;
    private reconnectTimeout: number = 3000;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 5;
    private handlers: Map<string, Set<(data: any) => void>> = new Map();

    public isConnected: Ref<boolean> = ref(false);
    public lastMessage: Ref<WebSocketMessage | null> = ref(null);

    private constructor() {}

    public static getInstance(): WebSocketService {
        if (!WebSocketService.instance) {
            WebSocketService.instance = new WebSocketService();
        }
        return WebSocketService.instance;
    }

    public connect(url: string): void {
        if (this.socket?.readyState === WebSocket.OPEN) {
            console.warn('WebSocket is already connected');
            return;
        }

        this.socket = new WebSocket(url);
        this.setupEventHandlers();
    }

    public disconnect(): void {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
            this.isConnected.value = false;
        }
    }

    public on(event: string, callback: (data: any) => void): void {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, new Set());
        }
        this.handlers.get(event)?.add(callback);
    }

    public off(event: string, callback: (data: any) => void): void {
        this.handlers.get(event)?.delete(callback);
    }

    public emit(event: string, data: any): void {
        if (this.socket?.readyState === WebSocket.OPEN) {
            const message: WebSocketMessage = {
                event,
                data,
                timestamp: Date.now()
            };
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    private setupEventHandlers(): void {
        if (!this.socket) return;

        this.socket.onopen = () => {
            this.isConnected.value = true;
            this.reconnectAttempts = 0;
            console.log('WebSocket connected');
        };

        this.socket.onclose = () => {
            this.isConnected.value = false;
            console.log('WebSocket closed');
            this.tryReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.socket.onmessage = (event) => {
            try {
                const message: WebSocketMessage = JSON.parse(event.data);
                this.lastMessage.value = message;
                
                const handlers = this.handlers.get(message.event);
                if (handlers) {
                    handlers.forEach(handler => handler(message.data));
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
    }

    private tryReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        setTimeout(() => {
            this.reconnectAttempts++;
            if (this.socket?.url) {
                console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect(this.socket.url);
            }
        }, this.reconnectTimeout * this.reconnectAttempts);
    }
}