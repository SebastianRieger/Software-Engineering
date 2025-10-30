export class StorageService {
    private static instance: StorageService;
    private prefix: string = 'nimrag_';

    private constructor() {}

    public static getInstance(): StorageService {
        if (!StorageService.instance) {
            StorageService.instance = new StorageService();
        }
        return StorageService.instance;
    }

    public setItem(key: string, value: any): void {
        try {
            const serializedValue = JSON.stringify(value);
            localStorage.setItem(this.getKey(key), serializedValue);
        } catch (error) {
            console.error(`Error saving to localStorage:`, error);
            throw new Error('Failed to save data to localStorage');
        }
    }

    public getItem<T>(key: string, defaultValue: T | null = null): T | null {
        try {
            const item = localStorage.getItem(this.getKey(key));
            if (item === null) return defaultValue;
            return JSON.parse(item) as T;
        } catch (error) {
            console.error(`Error reading from localStorage:`, error);
            return defaultValue;
        }
    }

    public removeItem(key: string): void {
        localStorage.removeItem(this.getKey(key));
    }

    public clear(): void {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith(this.prefix)) {
                localStorage.removeItem(key);
            }
        });
    }

    public hasItem(key: string): boolean {
        return localStorage.getItem(this.getKey(key)) !== null;
    }

    private getKey(key: string): string {
        return `${this.prefix}${key}`;
    }
}

// Export a singleton instance
export const storage = StorageService.getInstance();