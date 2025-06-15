import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { MetricAlert, AlertSeverity } from '../../../types/metrics';

// Updated to match simplified backend disk data structure
export interface DiskMetric {
    percent: number;
    total: number;
    used: number;
    free: number;
    read_bytes: number;
    write_bytes: number;
    read_rate: number;
    write_rate: number;
    partitions: {
        device: string;
        mountpoint: string;
        fstype: string;
        opts: string;
        total: number;
        used: number;
        free: number;
        percent: number;
    }[];
    io_counters: {
        [disk: string]: {
            read_count: number;
            write_count: number;
            read_bytes: number;
            write_bytes: number;
            read_time: number;
            write_time: number;
            busy_time: number;
        };
    };
}

export interface DiskThresholds {
    usage: {
        warning: number;
        critical: number;
    };
}

export interface DiskState {
    current: DiskMetric | null;
    historical: DiskMetric[];
    alerts: MetricAlert[];
    thresholds: DiskThresholds;
    diskLoading: boolean;
    diskError: string | null;
    lastUpdated: string | null;
}

const initialState: DiskState = {
    current: null,
    historical: [],
    alerts: [],
    thresholds: {
        usage: {
            warning: 80,
            critical: 95
        }
    },
    diskLoading: false,
    diskError: null,
    lastUpdated: null
};

// Helper function to check disk thresholds and generate alerts
const checkThresholds = (metrics: DiskMetric, thresholds: DiskThresholds): MetricAlert[] => {
    const alerts: MetricAlert[] = [];
    const now = new Date().toISOString();

    // Check disk usage threshold
    if (metrics.percent >= thresholds.usage.critical) {
        alerts.push({
            id: `disk-usage-${Date.now()}`,
            metric_type: 'disk',
            type: 'usage',
            severity: AlertSeverity.HIGH,
            threshold: thresholds.usage.critical,
            current_value: metrics.percent,
            timestamp: now,
            message: `Disk usage critical: ${metrics.percent.toFixed(1)}%`
        });
    } else if (metrics.percent >= thresholds.usage.warning) {
        alerts.push({
            id: `disk-usage-${Date.now()}`,
            metric_type: 'disk',
            type: 'usage',
            severity: AlertSeverity.MEDIUM,
            threshold: thresholds.usage.warning,
            current_value: metrics.percent,
            timestamp: now,
            message: `Disk usage high: ${metrics.percent.toFixed(1)}%`
        });
    }

    return alerts;
};

const diskSlice = createSlice({
    name: 'disk',
    initialState,
    reducers: {
        setDiskLoading: (state, action: PayloadAction<boolean>) => {
            state.diskLoading = action.payload;
        },
        setDiskError: (state, action: PayloadAction<string | null>) => {
            state.diskError = action.payload;
            state.diskLoading = false;
        },
        updateDiskMetrics: (state, action: PayloadAction<DiskMetric>) => {
            console.log(' Disk Slice - updateDiskMetrics called with payload:', action.payload);
            
            const newMetric = action.payload;
            state.current = newMetric;
            state.historical = [...state.historical, newMetric].slice(-1000); // Keep last 1000 readings
            state.lastUpdated = new Date().toISOString();
            
            // Check for threshold violations
            const alerts = checkThresholds(newMetric, state.thresholds);
            if (alerts.length > 0) {
                state.alerts = [...state.alerts, ...alerts].slice(-50); // Keep last 50 alerts
            }
            
            state.diskLoading = false;
            state.diskError = null;
            
            console.log(' Disk Slice - update complete, current usage:', state.current?.percent);
        },
        updateThresholds: (state, action: PayloadAction<Partial<DiskThresholds>>) => {
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
            state.diskLoading = false;
            state.diskError = null;
            state.lastUpdated = null;
        }
    }
}); 

// Export actions
export const {
    setDiskLoading,
    setDiskError,
    updateDiskMetrics,
    updateThresholds,
    clearAlerts,
    reset
} = diskSlice.actions;

// Export selectors
export const selectDiskMetrics = (state: { disk: DiskState }) => state.disk.current;
export const selectDiskHistorical = (state: { disk: DiskState }) => state.disk.historical;
export const selectDiskAlerts = (state: { disk: DiskState }) => state.disk.alerts;
export const selectDiskThresholds = (state: { disk: DiskState }) => state.disk.thresholds;
export const selectDiskLoading = (state: { disk: DiskState }) => state.disk.diskLoading;
export const selectDiskError = (state: { disk: DiskState }) => state.disk.diskError;
export const selectDiskLastUpdated = (state: { disk: DiskState }) => state.disk.lastUpdated;

export default diskSlice.reducer;