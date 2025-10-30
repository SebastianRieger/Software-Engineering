import { defineStore } from 'pinia';
import type { Theme } from '../types';
import { storage } from '../services/storage.service';

interface ThemeState {
    currentTheme: Theme | null;
    isDarkMode: boolean;
}

const defaultTheme: Theme = {
    name: 'light',
    colors: {
        primary: '#007AFF',
        secondary: '#5856D6',
        background: '#FFFFFF',
        surface: '#F2F2F7',
        text: '#000000',
        error: '#FF3B30',
        warning: '#FF9500',
        success: '#34C759'
    },
    typography: {
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: {
            xs: '0.75rem',
            sm: '0.875rem',
            base: '1rem',
            lg: '1.125rem',
            xl: '1.25rem'
        },
        fontWeight: {
            normal: 400,
            medium: 500,
            bold: 700
        }
    },
    spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
        xl: '2rem'
    },
    isDark: false
};

export const useThemeStore = defineStore('theme', {
    state: (): ThemeState => ({
        currentTheme: storage.getItem('theme', defaultTheme),
        isDarkMode: (storage.getItem('isDarkMode', false) ?? false) as boolean
    }),

    getters: {
        theme: (state) => state.currentTheme || defaultTheme,
        isDark: (state) => state.isDarkMode
    },

    actions: {
        setTheme(theme: Theme) {
            this.currentTheme = theme;
            storage.setItem('theme', theme);
            this.applyTheme();
        },

        toggleDarkMode() {
            this.isDarkMode = !this.isDarkMode;
            storage.setItem('isDarkMode', this.isDarkMode);
            this.applyTheme();
        },
        applyTheme() {
            const theme = this.currentTheme || defaultTheme;
            const root = document.documentElement;

            // Anwenden der Farben auf CSS-Variablen
            Object.entries(theme.colors).forEach(([key, value]) => {
                root.style.setProperty(`--color-${key}`, String(value));
            });

            // Anwenden der Typographie
            root.style.setProperty('--font-family', String(theme.typography.fontFamily));
            Object.entries(theme.typography.fontSize).forEach(([key, value]) => {
                root.style.setProperty(`--font-size-${key}`, String(value));
            });

            // Anwenden der Abstände
            Object.entries(theme.spacing).forEach(([key, value]) => {
                root.style.setProperty(`--spacing-${key}`, String(value));
            });

            // Dark Mode Klasse
            if (this.isDarkMode) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        }
    }
});