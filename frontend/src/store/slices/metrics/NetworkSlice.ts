import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { MetricAlert, AlertSeverity } from '../../../types/metrics';

// Updated to match simplified backend network data structure
export interface NetworkMetric {
    bytes_sent: number;
    bytes_recv: number;
    packets_sent: number;
    packets_recv: number;
    sent_rate: number;
    recv_rate: number;
    interfaces: {
        name: string;
        address: string;
        mac_address: string;
        isup: boolean;
        speed: number;
        mtu: number;
    }[];
    connections: {
        fd: number | null;
        pid: number | null;
        type: string;
        local_address: string;
        remote_address: string;
        status: string;
    }[];
    connection_stats: {
        ESTABLISHED: number;
        LISTEN: number;
        TIME_WAIT: number;
        CLOSE_WAIT: number;
        CLOSED: number;
        OTHER: number;
    };
    protocol_stats: {
        tcp: number;
        udp: number;
        tcp6: number;
        udp6: number;
    };
    latency: number | null;
    connection_quality: {
        packet_loss: number | null;
        jitter: number | null;
        bandwidth: number;
    };
    interface_stats: {
        [name: string]: {
            bytes_sent: number;
            bytes_recv: number;
            packets_sent: number;
            packets_recv: number;
            errin: number;
            errout: number;
            dropin: number;
            dropout: number;
        };
    };
}

export interface NetworkThresholds {
    bandwidth: {
        warning: number;
        critical: number;
    };
    connections: {
        warning: number;
        critical: number;
    };
}

export interface NetworkState {
    current: NetworkMetric | null;
    historical: NetworkMetric[];
    alerts: MetricAlert[];
    thresholds: NetworkThresholds;
    networkLoading: boolean;
    networkError: string | null;
    lastUpdated: string | null;
}

const initialState: NetworkState = {
    current: null,
    historical: [],
    alerts: [],
    thresholds: {
        bandwidth: {
            warning: 80000000, // 80 MB/s
            critical: 100000000 // 100 MB/s
        },
        connections: {
            warning: 500,
            critical: 1000
        }
    },
    networkLoading: false,
    networkError: null,
    lastUpdated: null
};

// Helper function to check network thresholds and generate alerts
const checkThresholds = (metrics: NetworkMetric, thresholds: NetworkThresholds): MetricAlert[] => {
    const alerts: MetricAlert[] = [];
    const now = new Date().toISOString();

    // Check bandwidth usage - use the correct field names from new backend
    const totalBandwidth = (metrics.sent_rate || 0) + (metrics.recv_rate || 0);
    if (totalBandwidth >= thresholds.bandwidth.critical) {
        alerts.push({
            id: `network-bandwidth-${Date.now()}`,
            metric_type: 'network',
            type: 'bandwidth',
            severity: AlertSeverity.HIGH,
            threshold: thresholds.bandwidth.critical,
            current_value: totalBandwidth,
            timestamp: now,
            message: `Network bandwidth critical: ${(totalBandwidth / 1000000).toFixed(1)} MB/s`
        });
    } else if (totalBandwidth >= thresholds.bandwidth.warning) {
        alerts.push({
            id: `network-bandwidth-${Date.now()}`,
            metric_type: 'network',
            type: 'bandwidth',
            severity: AlertSeverity.MEDIUM,
            threshold: thresholds.bandwidth.warning,
            current_value: totalBandwidth,
            timestamp: now,
            message: `Network bandwidth warning: ${(totalBandwidth / 1000000).toFixed(1)} MB/s`
        });
    }

    // Check connection count - use the correct field names from new backend
    const connectionStats = metrics.connection_stats || {};
    const totalConnections = Object.values(connectionStats).reduce((sum: number, count: any) => sum + (count || 0), 0);

    if (totalConnections >= thresholds.connections.critical) {
        alerts.push({
            id: `network-connections-${Date.now()}`,
            metric_type: 'network',
            type: 'connections',
            severity: AlertSeverity.HIGH,
            threshold: thresholds.connections.critical,
            current_value: totalConnections,
            timestamp: now,
            message: `Network connections critical: ${totalConnections} active connections`
        });
    } else if (totalConnections >= thresholds.connections.warning) {
        alerts.push({
            id: `network-connections-${Date.now()}`,
            metric_type: 'network',
            type: 'connections',
            severity: AlertSeverity.MEDIUM,
            threshold: thresholds.connections.warning,
            current_value: totalConnections,
            timestamp: now,
            message: `Network connections warning: ${totalConnections} active connections`
        });
    }

    return alerts;
};

export const networkSlice = createSlice({
    name: 'network',
    initialState,
    reducers: {
        setNetworkLoading: (state, action: PayloadAction<boolean>) => {
            state.networkLoading = action.payload;
        },
        setNetworkError: (state, action: PayloadAction<string | null>) => {
            state.networkError = action.payload;
            state.networkLoading = false;
        },
        updateNetworkMetrics: (state, action: PayloadAction<NetworkMetric>) => {
            console.log(' Network Slice - updateNetworkMetrics called with payload:', action.payload);

            const newMetric = action.payload;
            state.current = newMetric;
            state.historical = [...state.historical, newMetric].slice(-1000); // Keep last 1000 readings
            state.lastUpdated = new Date().toISOString();

            // Check for threshold violations
            const alerts = checkThresholds(newMetric, state.thresholds);
            if (alerts.length > 0) {
                state.alerts = [...state.alerts, ...alerts].slice(-50); // Keep last 50 alerts
            }

            state.networkLoading = false;
            state.networkError = null;

            console.log(' Network Slice - update complete, current bandwidth:',
                       (state.current?.sent_rate + state.current?.recv_rate) / 1000000);
        },
        updateThresholds: (state, action: PayloadAction<Partial<NetworkThresholds>>) => {
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
            state.networkLoading = false;
            state.networkError = null;
            state.lastUpdated = null;
        }
    }
});

// Export actions
export const {
    setNetworkLoading,
    setNetworkError,
    updateNetworkMetrics,
    updateThresholds,
    clearAlerts,
    reset
} = networkSlice.actions;

// Export selectors
export const selectNetworkMetrics = (state: { network: NetworkState }) => state.network.current;
export const selectNetworkHistorical = (state: { network: NetworkState }) => state.network.historical;
export const selectNetworkAlerts = (state: { network: NetworkState }) => state.network.alerts;
export const selectNetworkThresholds = (state: { network: NetworkState }) => state.network.thresholds;
export const selectNetworkLoading = (state: { network: NetworkState }) => state.network.networkLoading;
export const selectNetworkError = (state: { network: NetworkState }) => state.network.networkError;
export const selectNetworkLastUpdated = (state: { network: NetworkState }) => state.network.lastUpdated;

// Export the reducer
export default networkSlice.reducer;
