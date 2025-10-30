// Core Types
export type ID = string | number;

// Theme Types
export interface ThemeColors {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    error: string;
    warning: string;
    success: string;
}

export interface Typography {
    fontFamily: string;
    fontSize: {
        xs: string;
        sm: string;
        base: string;
        lg: string;
        xl: string;
    };
    fontWeight: {
        normal: number;
        medium: number;
        bold: number;
    };
}

export interface Spacing {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
}

export interface Theme {
    name: string;
    colors: ThemeColors;
    typography: Typography;
    spacing: Spacing;
    isDark: boolean;
}

// Widget Types
export type WidgetType =
    | 'weather'
    | 'clock'
    | 'calendar'
    | 'smart-home'
    | 'news'
    | 'notes'
    | 'music'

export interface Position {
    x: number;
    y: number;
    z?: number;
}

export interface Size {
    width: number;
    height: number;
    minWidth?: number;
    minHeight?: number;
}

export interface WidgetConfig {
    position: Position;
    size: Size;
    refreshInterval: number;
    settings: Record<string, any>;
}

export interface Widget {
    id: ID;
    type: WidgetType;
    title: string;
    config: WidgetConfig;
    data?: any;
    isEnabled: boolean;
}