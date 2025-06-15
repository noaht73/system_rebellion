import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { MetricAlert, AlertSeverity } from '../../../types/metrics';

// Updated to match simplified backend memory data structure
export interface MemoryMetric {
    timestamp: string | number | Date;
    total: number;
    available: number;
    used: number;
    free: number;
    percent: number;
    cached: number;
    buffers: number;
    shared: number;
    swap: {
        total: number;
        used: number;
        free: number;
        percent: number;
        sin: number;
        sout: number;
    };
    top_processes: {
        pid: number;
        name: string;
        username: string;
        memory_percent: number;
        memory_mb: number;
    }[];
}

export interface MemoryThresholds {
    usage: {
        warning: number;
        critical: number;
    };
}

export interface MemoryState {
    current: MemoryMetric | null;
    historical: MemoryMetric[];
    alerts: MetricAlert[];
    thresholds: MemoryThresholds;
    memoryLoading: boolean;
    memoryError: string | null;
    lastUpdated: string | null;
}

const initialState: MemoryState = {
    current: null,
    historical: [],
    alerts: [],
    thresholds: {
        usage: {
            warning: 80,
            critical: 95
        }
    },
    memoryLoading: false,
    memoryError: null,
    lastUpdated: null
};

// Helper function to check memory thresholds and generate alerts
const checkThresholds = (metrics: MemoryMetric, thresholds: MemoryThresholds): MetricAlert[] => {
    const alerts: MetricAlert[] = [];
    const now = new Date().toISOString();

    // Check memory usage threshold
    if (metrics.percent >= thresholds.usage.critical) {
        alerts.push({
            id: `memory-usage-${Date.now()}`,
            metric_type: 'memory',
            type: 'usage',
            severity: AlertSeverity.HIGH,
            threshold: thresholds.usage.critical,
            current_value: metrics.percent,
            timestamp: now,
            message: `Memory usage critical: ${metrics.percent.toFixed(1)}%`
        });
    } else if (metrics.percent >= thresholds.usage.warning) {
        alerts.push({
            id: `memory-usage-${Date.now()}`,
            metric_type: 'memory',
            type: 'usage',
            severity: AlertSeverity.MEDIUM,
            threshold: thresholds.usage.warning,
            current_value: metrics.percent,
            timestamp: now,
            message: `Memory usage high: ${metrics.percent.toFixed(1)}%`
        });
    }

    return alerts;
};

export const memorySlice = createSlice({
    name: 'memory',
    initialState,
    reducers: {
        setMemoryLoading: (state, action: PayloadAction<boolean>) => {
            state.memoryLoading = action.payload;
        },
        setMemoryError: (state, action: PayloadAction<string | null>) => {
            state.memoryError = action.payload;
            state.memoryLoading = false;
        },
        updateMemoryMetrics: (state, action: PayloadAction<MemoryMetric>) => {
            console.log(' Memory Slice - updateMemoryMetrics called with payload:', action.payload);
            
            const newMetric = action.payload;
            state.current = newMetric;
            state.historical = [...state.historical, newMetric].slice(-1000); // Keep last 1000 readings
            state.lastUpdated = new Date().toISOString();
            
            // Check for threshold violations
            const alerts = checkThresholds(newMetric, state.thresholds);
            if (alerts.length > 0) {
                state.alerts = [...state.alerts, ...alerts].slice(-50); // Keep last 50 alerts
            }
            
            state.memoryLoading = false;
            state.memoryError = null;
            
            console.log(' Memory Slice - update complete, current usage:', state.current?.percent);
        },
        updateThresholds: (state, action: PayloadAction<Partial<MemoryThresholds>>) => {
            state.thresholds = {
                ...state.thresholds,
                ...action.payload
            };
        },
        clearAlerts: (state) => {
            state.alerts = [];
        },
        reset: (state) => {
            state.current = null;
            state.historical = [];
            state.alerts = [];
            state.memoryLoading = false;
            state.memoryError = null;
            state.lastUpdated = null;
        }
    }
});

// Export actions
export const {
    setMemoryLoading,
    setMemoryError,
    updateMemoryMetrics,
    updateThresholds,
    clearAlerts,
    reset
} = memorySlice.actions;

// Export selectors
export const selectMemoryMetrics = (state: { memory: MemoryState }) => state.memory.current;
export const selectMemoryHistorical = (state: { memory: MemoryState }) => state.memory.historical;
export const selectMemoryAlerts = (state: { memory: MemoryState }) => state.memory.alerts;
export const selectMemoryThresholds = (state: { memory: MemoryState }) => state.memory.thresholds;
export const selectMemoryLoading = (state: { memory: MemoryState }) => state.memory.memoryLoading;
export const selectMemoryError = (state: { memory: MemoryState }) => state.memory.memoryError;
export const selectMemoryLastUpdated = (state: { memory: MemoryState }) => state.memory.lastUpdated;

// Export the reducer
export default memorySlice.reducer;