// frontend/src/components/metrics/disk/DiskMetric.tsx

import React, { useState } from 'react';
import { useAppSelector } from '../../../store/hooks';
import { selectDiskMetrics } from '../../../store/slices/metrics/DiskSlice';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { MetricsCard, MetricStatus } from '../../../design-system/components/MetricsCard';
import Tabs, { Tab } from '../../../design-system/components/Tabs';
import ErrorDisplay from '../../../components/common/ErrorDisplay';
import LoadingIndicator from '../../../components/common/LoadingIndicator';
import DiskPartitionsTab from './tabs/DiskPartitionsTab';
import { DiskDirectoryTab } from './tabs/DiskDirectoryTab';
import { DiskPerformanceTab } from './tabs/DiskPerformanceTab';
import { processDiskData } from './utils/diskDataProcessor';
import { DiskMetricProps, RawDiskMetrics, DiskPartition } from './tabs/types';
import './DiskMetric.css';

// Extended props to support dashboard mode
interface ConsolidatedDiskMetricProps extends DiskMetricProps {
  isDashboard?: boolean; // Whether this is being used in the dashboard
  height?: number | string;
}

export const DiskMetric: React.FC<ConsolidatedDiskMetricProps> = ({ 
  compact = false,
  defaultTab = 'partitions',
  isDashboard = true,
  height
}) => {
  type TabType = 'partitions' | 'directory' | 'performance' | 'overview';
  const [activeTab, setActiveTab] = useState<TabType>(defaultTab as TabType);
  
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId as TabType);
  };

  // Get disk metrics from the main metrics slice
  const currentMetric = useAppSelector(selectDiskMetrics);
  const loading = !currentMetric;
  const error = !currentMetric ? 'No metrics data available' : null;
  const diskMetrics = currentMetric;
  
  // Handle loading state
  if (loading) {
    return isDashboard ? (
      <MetricsCard title="Disk Usage" value="--" unit="%" updating={true} />
    ) : (
      <LoadingIndicator message="Fetching disk metrics..." />
    );
  }
  
  // Handle error state
  if (error || !diskMetrics) {
    return isDashboard ? (
      <div className={`disk-metric ${compact ? 'compact' : ''}`} style={{ height }}>
        <MetricsCard title="Disk Usage" value="--" unit="%" status="critical" />
      </div>
    ) : (
      <ErrorDisplay 
        message="Unable to load disk metrics" 
        details={typeof error === 'string' ? error : 'Unknown error occurred'} 
        retry={() => {}} 
      />
    );
  }

  // Extract disk data from metrics - use the correct field names from new backend
  console.log(' Disk Component - New backend data structure:', diskMetrics);
  
  const diskUsage = diskMetrics?.percent || 0;

  // Map the raw partition data to the structure expected by RawDiskMetrics
  const mappedPartitions: DiskPartition[] = (diskMetrics?.partitions || []).map((p: any) => ({
    mountPoint: p.mountpoint,
    device: p.device,
    fsType: p.fstype,
    total: p.total,
    used: p.used,
    available: p.free,
    percentUsed: p.percent,
    // Provide default values for other fields required by the DiskPartition type
    inodes: { total: 0, used: 0, free: 0, percentUsed: 0 },
    health: { status: 'healthy', issues: [], errors: 0, lastCheckTime: 0 },
    readOnly: p.opts ? p.opts.includes('ro') : false,
    physicalDiskId: '',
  }));

  // Create RawDiskMetrics structure from available metrics
  const rawDiskMetrics: RawDiskMetrics = {
    partitions: mappedPartitions,
    physicalDisks: [], // No data from backend for this
    directories: [],   // No data from backend for this
    performance: {
      current: {
        readSpeed: diskMetrics?.read_rate || 0,
        writeSpeed: diskMetrics?.write_rate || 0,
        readIOPS: 0,
        writeIOPS: 0,
        utilization: diskUsage,
        queueDepth: 0,
        latency: {
          read: 0,
          write: 0
        }
      },
      bottlenecks: {
        detected: false,
        type: null,
        severity: null,
        cause: null,
        recommendations: []
      },
      topProcesses: []
    },
    history: [] // No data from backend for this
  };

  // Process disk data once for all tabs
  const processedData = processDiskData(rawDiskMetrics);
  
  // Format bytes to human-readable format
  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  // Calculate disk status
  const getStatus = (usage: number): MetricStatus => {
    if (usage >= 90) return 'critical';
    if (usage >= 70) return 'warning';
    return 'normal';
  };

  // Colors for pie chart
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

  // If using dashboard mode, render the dashboard style
  if (isDashboard) {
    // Prepare partition data for pie chart
    const partitionData = processedData.partitions.items.map((partition) => ({
      name: partition.mountPoint,
      value: partition.used
    }));

    return (
      <div className="disk-metric" style={{ height }}>
        <MetricsCard
          title="Disk Usage"
          value={`${diskUsage.toFixed(1)}`}
          unit="%"
          status={getStatus(diskUsage)}
        >
          <Tabs activeTab={activeTab} onChange={handleTabChange}>
            <Tab id="overview" label="Overview">
              <div className="overview-content">
                <div className="partitions-chart">
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={partitionData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {partitionData.map((_entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatBytes(value as number)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="disk-io-info">
                  <div className="disk-io-rate">
                    <span>I/O Rate:</span>
                    <span>{formatBytes(processedData.performance.current.readSpeed + processedData.performance.current.writeSpeed)}/s</span>
                  </div>
                </div>
              </div>
            </Tab>
            <Tab id="partitions" label="Partitions">
              <div className="partitions-list">
                {processedData.partitions.items.map((partition: { mountPoint: string | number | bigint | boolean | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | React.ReactPortal | Promise<string | number | bigint | boolean | React.ReactPortal | React.ReactElement<unknown, string | React.JSXElementConstructor<any>> | Iterable<React.ReactNode> | null | undefined> | null | undefined; percentUsed: number; total: number; used: number; available: number; }, index: React.Key | null | undefined) => (
                  <div key={index} className="partition-card">
                    <div className="partition-name">{partition.mountPoint}</div>
                    <div className="partition-usage">{partition.percentUsed.toFixed(1)}%</div>
                    <div className="partition-details">
                      <span>Total: {formatBytes(partition.total)}</span>
                      <span>Used: {formatBytes(partition.used)}</span>
                      <span>Free: {formatBytes(partition.available)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Tab>
            <Tab id="performance" label="Performance">
              <div className="performance-content">
                <h3>Disk Performance</h3>
                <div className="performance-metrics">
                  <div className="performance-metric">
                    <span>I/O Rate:</span>
                    <span>{formatBytes(processedData.performance.current.readSpeed + processedData.performance.current.writeSpeed)}/s</span>
                  </div>
                  <div className="performance-metric">
                    <span>Read Rate:</span>
                    <span>{formatBytes(processedData.performance.current.readSpeed)}/s</span>
                  </div>
                  <div className="performance-metric">
                    <span>Write Rate:</span>
                    <span>{formatBytes(processedData.performance.current.writeSpeed)}/s</span>
                  </div>
                </div>
              </div>
            </Tab>
          </Tabs>
        </MetricsCard>
      </div>
    );
  }
  // Render full tabbed version for component mode
  return (
    <div className={`disk-metric ${compact ? 'compact' : ''}`}>
      <Tabs activeTab={activeTab} onChange={handleTabChange}>
        <Tab id="partitions" label="Partitions">
          <DiskPartitionsTab data={processedData} compact={compact} />
        </Tab>
        <Tab id="directory" label="Directory Usage">
          <DiskDirectoryTab data={processedData} />
        </Tab>
        <Tab id="performance" label="Performance">
          <DiskPerformanceTab data={processedData} />
        </Tab>
      </Tabs>
    </div>
  );
};

export default DiskMetric;