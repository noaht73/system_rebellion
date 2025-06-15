// frontend/src/components/metrics/NetworkMetrics/NetworkMetric.tsx

import React, { useState } from 'react';
import { useAppSelector } from '../../../store/hooks';
import { selectNetworkMetrics, selectNetworkHistorical } from '../../../store/slices/metrics/NetworkSlice';
import { NetworkDetails } from '../../../types/metrics';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { MetricsCard, MetricStatus } from '../../../design-system/components/MetricsCard';
import Tabs, { Tab } from '../../../design-system/components/Tabs';
import ErrorDisplay from '../../common/ErrorDisplay';
import LoadingIndicator from '../../common/LoadingIndicator';
import NetworkOverviewTab from './tabs/NetworkOverviewTab';
import NetworkInterfacesTab from './tabs/NetworkInterfacesTab';
import NetworkConnectionsTab from './tabs/NetworkConnectionsTab';
import './NetworkMetric.css';

interface NetworkMetricProps {
  compact?: boolean;
  defaultTab?: string;
  dashboardMode?: boolean; // Whether this is being used in the dashboard
  height?: number | string;
}

export const NetworkMetric: React.FC<NetworkMetricProps> = ({ 
  compact = false,
  defaultTab = 'overview',
  dashboardMode = false,
  height
}) => {
  type TabType = 'overview' | 'interfaces' | 'connections' | 'history';
  const [activeTab, setActiveTab] = useState<TabType>(defaultTab as TabType);
  
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId as TabType);
  };

  // Get network metrics from the main metrics slice
  const currentMetric = useAppSelector(selectNetworkMetrics);
  const historicalMetrics = useAppSelector(selectNetworkHistorical);
  const loading = !currentMetric;
  const error = !currentMetric ? 'No metrics data available' : null;
  
  // Handle loading state
  if (loading) {
    return dashboardMode ? (
      <MetricsCard title="Network Traffic" value="--" unit="KB/s" updating={true} />
    ) : (
      <LoadingIndicator message="Fetching network metrics..." />
    );
  }
  
  // Handle error state
  if (error || !currentMetric) {
    return dashboardMode ? (
      <div className={`network-metric ${compact ? 'compact' : ''}`} style={{ height }}>
        <MetricsCard title="Network Traffic" value="--" unit="KB/s" status="critical" />
      </div>
    ) : (
      <ErrorDisplay 
        message="Unable to load network metrics" 
        details={typeof error === 'string' ? error : 'Unknown error occurred'} 
        retry={() => {}} 
      />
    );
  }

  // Extract network data from metrics - use the correct field names from new backend
  console.log(' Network Component - New backend data structure:', currentMetric);
  
  const bytesSent = currentMetric.bytes_sent || 0;
  const bytesRecv = currentMetric.bytes_recv || 0;
  const packetsSent = currentMetric.packets_sent || 0;
  const packetsRecv = currentMetric.packets_recv || 0;
  const sentRate = currentMetric.sent_rate || 0;
  const recvRate = currentMetric.recv_rate || 0;
  const interfaces = currentMetric.interfaces || [];
  const connections = currentMetric.connections || [];
  const connectionStats = currentMetric.connection_stats || {};
  const protocolStats = currentMetric.protocol_stats || {};
  const interfaceStats = currentMetric.interface_stats || {};
  const connectionQuality = currentMetric.connection_quality || {};
  
  // Debug logging for the new data structure
  console.log(' Network Component - New backend data structure:');
  console.log(' bytes_sent:', bytesSent);
  console.log(' bytes_recv:', bytesRecv);
  console.log(' sent_rate:', sentRate);
  console.log(' recv_rate:', recvRate);
  console.log(' interfaces length:', interfaces.length);
  console.log(' connections length:', connections.length);
  console.log(' connection_stats:', connectionStats);
  console.log(' protocol_stats:', protocolStats);
  
  // Handle the new data structure from the backend
  const networkDetails: NetworkDetails = {
    bytes_sent: bytesSent,
    bytes_recv: bytesRecv,
    packets_sent: packetsSent,
    packets_recv: packetsRecv,
    rate_mbps: (sentRate + recvRate) / (1024 * 1024), // Convert to MB/s
    sent_rate_bps: sentRate,
    recv_rate_bps: recvRate,
    io_stats: {
      bytes_sent: bytesSent,
      bytes_recv: bytesRecv,
      packets_sent: packetsSent,
      packets_recv: packetsRecv,
      sent_rate: sentRate,
      recv_rate: recvRate,
      errors_in: 0, // Would need to aggregate from interface_stats
      errors_out: 0,
      drops_in: 0,
      drops_out: 0
    },
    interfaces: interfaces,
    protocol_stats: {
      tcp: {
        active: protocolStats.tcp || 0,
        established: connectionStats.ESTABLISHED || 0,
        listening: connectionStats.LISTEN || 0
      },
      udp: {
        active: protocolStats.udp || 0
      },
      http: {
        connections: 0 // Not directly available
      },
      https: {
        connections: 0 // Not directly available
      },
      dns: {
        queries: 0 // Not directly available
      }
    },
    connection_quality: {
      average_latency: connectionQuality.latency || 0,
      packet_loss_percent: connectionQuality.packet_loss || 0,
      connection_stability: 100, // Default to good stability
      jitter: connectionQuality.jitter || 0,
      gateway_latency: 0, // Not available in current backend
      dns_latency: 0, // Not available in current backend
      internet_latency: 0 // Not available in current backend
    },
    protocol_breakdown: currentMetric.protocol_breakdown || {},
    top_bandwidth_processes: currentMetric.top_processes || []
  };

  // Calculate network rates for display
  const networkTransmitRate = sentRate;
  const networkReceiveRate = recvRate;
  const totalNetworkRate = networkTransmitRate + networkReceiveRate;

  // Prepare historical data for area chart
  const networkHistoryData = historicalMetrics.map(metric => ({
    timestamp: new Date(metric.timestamp).getTime(),
    receive: metric.recv_rate || 0,
    transmit: metric.sent_rate || 0,
    total: (metric.sent_rate || 0) + (metric.recv_rate || 0)
  }));

  // Process interfaces data
  const networkInterfaces = interfaces.map((iface: any) => ({
    name: iface.name || 'Unknown',
    address: iface.address || '',
    mac_address: iface.mac_address || '',
    isup: iface.isup || false,
    speed: iface.speed || 0,
    mtu: iface.mtu || 0,
    stats: interfaceStats[iface.name] || {
      bytes_sent: 0,
      bytes_recv: 0,
      packets_sent: 0,
      packets_recv: 0,
      errin: 0,
      errout: 0,
      dropin: 0,
      dropout: 0
    }
  }));

  // Process connections data
  const networkConnections = connections.map((conn: any) => ({
    fd: conn.fd || null,
    pid: conn.pid || null,
    type: conn.type || 'unknown',
    local_address: conn.local_address || '-',
    remote_address: conn.remote_address || '-',
    status: conn.status || 'UNKNOWN'
  }));

  // Format bytes to human-readable format
  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  // Format bytes per second
  const formatBytesPerSecond = (bytesPerSecond: number) => {
    return formatBytes(bytesPerSecond) + '/s';
  };

  // Calculate network status
  const getStatus = (rate: number): MetricStatus => {
    // These thresholds can be adjusted based on what's considered high network usage
    if (rate >= 10 * 1024 * 1024) return 'critical'; // 10 MB/s
    if (rate >= 5 * 1024 * 1024) return 'warning';   // 5 MB/s
    return 'normal';
  };

  // Prepare network data for component tabs
  const networkData = {
    overview: {
      receiveRate: networkReceiveRate,
      transmitRate: networkTransmitRate,
      totalReceived: networkDetails.bytes_recv || 0,
      totalTransmitted: networkDetails.bytes_sent || 0,
      packetErrors: networkDetails.io_stats?.errors_in || 0,
      packetDrops: networkDetails.io_stats?.drops_in || 0,
      io_stats: networkDetails.io_stats || {
        bytes_sent: networkDetails.bytes_sent || 0,
        bytes_recv: networkDetails.bytes_recv || 0,
        sent_rate: networkDetails.sent_rate_bps || 0,
        recv_rate: networkDetails.recv_rate_bps || 0,
        errors_in: 0,
        errors_out: 0,
        drops_in: 0,
        drops_out: 0
      },
      connection_quality: networkDetails.connection_quality || {
        average_latency: 0,
        packet_loss_percent: 0,
        connection_stability: 100,
        jitter: 0,
        gateway_latency: 0,
        dns_latency: 0,
        internet_latency: 0
      },
      protocol_breakdown: networkDetails.protocol_breakdown || {
        web: 30,
        email: 10,
        streaming: 25,
        gaming: 15,
        file_transfer: 10,
        other: 10
      },
      protocol_stats: networkDetails.protocol_stats || {
        tcp: { active: 0, established: 0 },
        udp: { active: 0 },
        http: { connections: 0 },
        https: { connections: 0 },
        dns: { queries: 0 }
      },
      top_bandwidth_processes: networkDetails.top_bandwidth_processes || []
    },
    interfaces: networkInterfaces,
    connections: networkConnections,
    history: networkHistoryData
  };

  // If using dashboard mode, render the dashboard style
  if (dashboardMode) {
    return (
      <div className="network-metric" style={{ height }}>
        <MetricsCard
          title="Network Traffic"
          value={formatBytes(totalNetworkRate / 1024).split(' ')[0]}
          unit={formatBytes(totalNetworkRate / 1024).split(' ')[1] + '/s'}
          status={getStatus(totalNetworkRate)}
        >
          <Tabs activeTab={activeTab} onChange={handleTabChange}>
            <Tab id="overview" label="Overview">
              <div className="overview-content">
                <div className="network-rates">
                  <div className="network-rate">
                    <span>Download:</span>
                    <span>{formatBytesPerSecond(networkReceiveRate)}</span>
                  </div>
                  <div className="network-rate">
                    <span>Upload:</span>
                    <span>{formatBytesPerSecond(networkTransmitRate)}</span>
                  </div>
                  <div className="network-rate">
                    <span>Total:</span>
                    <span>{formatBytesPerSecond(totalNetworkRate)}</span>
                  </div>
                </div>
              </div>
            </Tab>
            <Tab id="history" label="History">
              <div className="history-content">
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart
                    data={networkHistoryData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()} 
                    />
                    <YAxis tickFormatter={(value) => formatBytes(value).split(' ')[0] + ' ' + formatBytes(value).split(' ')[1]} />
                    <Tooltip 
                      labelFormatter={(timestamp) => new Date(timestamp as number).toLocaleString()}
                      formatter={(value, name) => [
                        formatBytesPerSecond(value as number), 
                        name === 'receive' ? 'Download' : name === 'transmit' ? 'Upload' : 'Total'
                      ]} 
                    />
                    <Area type="monotone" dataKey="receive" stackId="1" stroke="#8884d8" fill="#8884d8" name="Download" />
                    <Area type="monotone" dataKey="transmit" stackId="1" stroke="#82ca9d" fill="#82ca9d" name="Upload" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Tab>
            <Tab id="interfaces" label="Interfaces">
              <div className="interfaces-list">
                {networkInterfaces.map((iface, index) => (
                  <div key={index} className="interface-card">
                    <div className="interface-name">{iface.name}</div>
                    <div className="interface-status">{iface.isup ? 'Up' : 'Down'}</div>
                    <div className="interface-details">
                      <span>IP: {iface.address}</span>
                      <span>MAC: {iface.mac_address}</span>
                      <span>Download: {formatBytesPerSecond(iface.stats.bytes_recv || 0)}</span>
                      <span>Upload: {formatBytesPerSecond(iface.stats.bytes_sent || 0)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Tab>
          </Tabs>
        </MetricsCard>
      </div>
    );
  }
  
  // Render compact version for dashboard if requested
  if (compact) {
    return (
      <div className="network-metric network-metric--compact">
        <NetworkOverviewTab 
          data={networkData.overview} 
          historicalMetrics={networkData.history}
          compact={true} 
        />
      </div>
    );
  }
  
  // Render full tabbed version for component mode
  return (
    <div className={`network-metric ${compact ? 'compact' : ''}`}>
      <Tabs activeTab={activeTab} onChange={handleTabChange}>
        <Tab id="overview" label="Overview">
          <NetworkOverviewTab 
            data={networkData.overview} 
            historicalMetrics={networkData.history}
            compact={compact} 
          />
        </Tab>
        <Tab id="interfaces" label="Interfaces">
          <NetworkInterfacesTab interfaces={networkData.interfaces} />
        </Tab>
        <Tab id="connections" label="Connections">
          <NetworkConnectionsTab 
            connections={networkData.connections} 
            processes={networkData.overview.top_bandwidth_processes} 
          />
        </Tab>
        <Tab id="history" label="History">
          <div className="history-content">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart
                data={networkData.history}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()} 
                />
                <YAxis tickFormatter={(value) => formatBytes(value).split(' ')[0] + ' ' + formatBytes(value).split(' ')[1]} />
                <Tooltip 
                  labelFormatter={(timestamp) => new Date(timestamp as number).toLocaleString()}
                  formatter={(value, name) => [
                    formatBytesPerSecond(value as number), 
                    name === 'receive' ? 'Download' : name === 'transmit' ? 'Upload' : 'Total'
                  ]} 
                />
                <Legend />
                <Area type="monotone" dataKey="receive" stroke="#8884d8" fill="#8884d8" name="Download" />
                <Area type="monotone" dataKey="transmit" stroke="#82ca9d" fill="#82ca9d" name="Upload" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Tab>
      </Tabs>
    </div>
  );
};

export default NetworkMetric;