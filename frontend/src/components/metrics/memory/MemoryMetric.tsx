// frontend/src/components/metrics/memory/MemoryMetric.tsx

import React, { useState } from 'react';
import { useAppSelector } from '../../../store/hooks';
import { selectMemoryMetrics, selectMemoryHistorical } from '../../../store/slices/metrics/MemorySlice';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { MetricsCard, MetricStatus } from '../../../design-system/components/MetricsCard';
import Tabs, { Tab } from '../../../design-system/components/Tabs';
import ErrorDisplay from '../../../components/common/ErrorDisplay';
import LoadingIndicator from '../../../components/common/LoadingIndicator';
import { MemoryAllocationTab } from './tabs/MemoryAllocationTab';
import { MemoryProcessesTab } from './tabs/MemoryProcessesTab';
import { MemoryOverviewTab } from './tabs/MemoryOverviewTab';
import { ProcessedMemoryData, MemoryProcess } from './tabs/types';
import './MemoryMetric.css';

interface MemoryMetricProps {
  compact?: boolean;
  defaultTab?: string;
  dashboardMode?: boolean; // Whether this is being used in the dashboard
  height?: number | string;
}

export const MemoryMetric: React.FC<MemoryMetricProps> = ({ 
  compact = false,
  defaultTab = 'usage',
  dashboardMode = false,
  height
}) => {
  type TabType = 'overview' | 'processes' | 'allocation';
  const [activeTab, setActiveTab] = useState<TabType>(defaultTab as TabType);
  
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId as TabType);
  };

  // Get memory metrics from the main metrics slice
  const currentMetric = useAppSelector(selectMemoryMetrics);
  const historicalMetrics = useAppSelector(selectMemoryHistorical);
  const loading = !currentMetric;
  const error = !currentMetric ? 'No metrics data available' : null;
  
  // Handle loading state
  if (loading) {
    return dashboardMode ? (
      <MetricsCard title="Memory Usage" value="--" unit="%" updating={true} />
    ) : (
      <LoadingIndicator message="Fetching memory metrics..." />
    );
  }
  
  // Handle error state
  if (error || !currentMetric?.percent) {
    return dashboardMode ? (
      <div className={`memory-metric ${compact ? 'compact' : ''}`} style={{ height }}>
        <MetricsCard title="Memory Usage" value="--" unit="%" status="critical" />
      </div>
    ) : (
      <ErrorDisplay 
        message="Unable to load memory metrics" 
        details={typeof error === 'string' ? error : 'Unknown error occurred'} 
        retry={() => {}} 
      />
    );
  }

  // Extract memory data from metrics - use the correct field names from new backend
  const memoryUsage = currentMetric.percent || 0;
  const totalMemory = currentMetric.total || 0;
  const usedMemory = currentMetric.used || 0;
  const freeMemory = currentMetric.free || 0;
  const availableMemory = currentMetric.available || 0;
  const cachedMemory = currentMetric.cached || 0;
  const buffersMemory = currentMetric.buffers || 0;
  const sharedMemory = currentMetric.shared || 0;
  
  // Extract swap data
  const swapData = currentMetric.swap || {};
  const swapTotal = swapData.total || 0;
  const swapUsed = swapData.used || 0;
  const swapFree = swapData.free || 0;
  const swapPercent = swapData.percent || 0;
  
  // Extract top processes
  const topProcesses = currentMetric.top_processes || [];

  // Debug logging for the new data structure
  console.log('🔧 Memory Component - New backend data structure:');
  console.log('🔧 percent:', currentMetric.percent);
  console.log('🔧 total:', currentMetric.total);
  console.log('🔧 used:', currentMetric.used);
  console.log('🔧 available:', currentMetric.available);
  console.log('🔧 swap:', swapData);
  console.log('🔧 top_processes length:', topProcesses.length);

  // Process raw metrics into the format expected by tab components
  const processedData: ProcessedMemoryData = {
    overview: {
      physicalMemory: {
        total: totalMemory,
        used: usedMemory,
        free: freeMemory,
        percentUsed: memoryUsage
      },
      swap: {
        total: swapTotal,
        used: swapUsed,
        free: swapFree,
        percentUsed: swapPercent
      },
      cached: cachedMemory,
      active: availableMemory, // Using availableMemory as a substitute for active memory
      buffers: buffersMemory,
      pressureLevel: 'low', // Default to low if not available
      pressureIndicators: {
        pageInRate: 0, // These would come from metrics in a real implementation
        pageOutRate: 0,
        swapUsageRate: swapPercent
      }
    },
    processes: {
      topConsumers: topProcesses.map((proc: any) => ({
        pid: proc.pid || 0,
        name: proc.name || 'Unknown',
        command: proc.command || '',
        rss: proc.memory_usage || 0,
        vms: 0, // Default value
        shared: sharedMemory, // Default value
        percentMemory: proc.memory_percent || 0
      })) as MemoryProcess[],
      growthTrends: [],
      potentialLeaks: []
    },
    allocation: {
      byType: [
        {
          type: 'Used',
          bytes: usedMemory,
          percentage: memoryUsage
        },
        {
          type: 'Free',
          bytes: freeMemory,
          percentage: 100 - memoryUsage
        }
      ],
      fragmentation: {
        index: 0, // These would come from metrics in a real implementation
        largestBlock: 0,
        freeChunks: 0,
        rating: 'good'
      },
      optimizationRecommendations: []
    }
  };

  // Format bytes to human-readable format
  const formatBytes = (bytes: number, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  // Prepare historical data for area chart
  const memoryHistoryData = historicalMetrics.map(metric => ({
    timestamp: new Date(metric.timestamp).getTime(),
    usage: metric.percent
  }));

  // Calculate memory status
  const getStatus = (usage: number): MetricStatus => {
    if (usage >= 90) return 'critical';
    if (usage >= 70) return 'warning';
    return 'normal';
  };

  // Colors for pie chart
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  // Prepare memory data for charts
  const memoryPieData = [
    { name: 'Used', value: usedMemory },
    { name: 'Free', value: freeMemory },
    { name: 'Cached', value: cachedMemory },
    { name: 'Buffers', value: buffersMemory }
  ];
  
  // If using dashboard mode, render the dashboard style
  if (dashboardMode) {
    return (
      <div className="memory-metric" style={{ height }}>
        <MetricsCard
          title="Memory Usage"
          value={`${memoryUsage.toFixed(1)}`}
          unit="%"
          status={getStatus(memoryUsage)}
        >
          <Tabs activeTab={activeTab} onChange={handleTabChange}>
            <Tab id="overview" label="Overview">
              <div className="overview-content">
                <div className="memory-chart">
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={memoryPieData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {memoryPieData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatBytes(value as number)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="memory-details">
                  <div className="memory-detail">
                    <span>Total:</span>
                    <span>{formatBytes(totalMemory)}</span>
                  </div>
                  <div className="memory-detail">
                    <span>Used:</span>
                    <span>{formatBytes(usedMemory)}</span>
                  </div>
                  <div className="memory-detail">
                    <span>Free:</span>
                    <span>{formatBytes(freeMemory)}</span>
                  </div>
                </div>
              </div>
            </Tab>
            <Tab id="history" label="History">
              <div className="history-content">
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart
                    data={memoryHistoryData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()} 
                    />
                    <YAxis domain={[0, 100]} />
                    <Tooltip 
                      labelFormatter={(timestamp) => new Date(timestamp as number).toLocaleString()}
                      formatter={(value) => [`${value}%`, 'Memory Usage']} 
                    />
                    <Area type="monotone" dataKey="usage" stroke="#8884d8" fill="#8884d8" />
                  </AreaChart>
                </ResponsiveContainer>
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
      <div className="memory-metric memory-metric--compact">
        <MemoryOverviewTab 
          data={processedData}
          compact={true} 
        />
      </div>
    );
  }
  
  // Render full tabbed version for component mode
  return (
    <div className={`memory-metric ${compact ? 'compact' : ''}`}>
      <Tabs activeTab={activeTab} onChange={handleTabChange}>
        <Tab id="overview" label="Overview">
          <MemoryOverviewTab 
            data={processedData}
            compact={compact} 
          />
        </Tab>
        <Tab id="processes" label="Processes">
          <MemoryProcessesTab data={processedData} />
        </Tab>
        <Tab id="allocation" label="Allocation">
          <MemoryAllocationTab 
            data={processedData}
          />
        </Tab>
      </Tabs>
    </div>
  );
};

export default MemoryMetric;