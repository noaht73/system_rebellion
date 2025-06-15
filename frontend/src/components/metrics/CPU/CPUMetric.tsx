// frontend/src/components/metrics/CPU/CPUMetric.tsx

import React, { useState } from 'react';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart, BarChart, Bar } from 'recharts';
import { useAppSelector } from '../../../store/hooks';
import { 
  selectCPUMetrics, 
  selectCPUHistorical, 
  selectCPULoading,
  selectCPUError,
  type CPUMetric 
} from '../../../store/slices/metrics/CPUSlice';
import { MetricsCard, MetricStatus } from '../../../design-system/components/MetricsCard';
import { Tabs, Tab } from '../../../design-system/components/Tabs/Tabs';
import { Card } from '../../../design-system/components/Card/Card';
import CPUOverviewTab from './Tabs/CPUOverviewTab';
import CPUProcessesTab from './Tabs/CPUProcessesTab';
import CPUCoresTab from './Tabs/CPUCoresTab';
import CPUThermalTab from './Tabs/CPUThermalTab';
import './CPUMetric.css'

// Interface for CPU process
interface CPUProcess {
  name: string;
  pid: number;
  cpu_percent: number;
  memory_percent: number;
}

// Interface for CPU details
interface CPUDetails {
  cores: {
    logical: number;
    physical: number;
  };
  frequency: {
    current: number;
    min: number;
    max: number;
  };
  temperature: number;
  per_core_usage: number[];
  physical_cores?: number; // Added to match the expected property
}

type CPUTabType = 'overview' | 'processes' | 'cores' | 'thermal';

interface CPUMetricProps {
  compact?: boolean;
  showTabs?: boolean;
  initialTab?: CPUTabType;
  height?: number | string;
  dashboardMode?: boolean; // Whether this is being used in the dashboard
}

const CPUMetric: React.FC<CPUMetricProps> = ({
  compact = false,
  showTabs = true,
  initialTab = 'overview',
  height,
  dashboardMode = false,
}) => {
  // Redux state - Get metrics from the central metrics slice
  const currentMetric = useAppSelector(selectCPUMetrics) || {} as any;
  const historicalMetrics = useAppSelector(selectCPUHistorical) || [];
  const isLoading = useAppSelector(selectCPULoading);
  const error = useAppSelector(selectCPUError);

  console.log(' CPUMetric Component - Redux state received:');
  console.log(' currentMetric:', currentMetric);
  console.log(' historicalMetrics length:', historicalMetrics.length);
  console.log(' isLoading:', isLoading);
  console.log(' error:', error);

  // Local state
  const [activeTab, setActiveTab] = useState<CPUTabType>(initialTab);

  // If loading or error, show appropriate message
  if (isLoading) {
    console.log(' CPUMetric Component - Showing loading state');
    return (
      <div className={`metric-card ${compact ? 'compact' : ''}`} style={{ height }}>
        <h3>CPU Activity</h3>
        <div className="loading-message">Loading CPU metrics...</div>
      </div>
    );
  }

  // Extract CPU usage from the metric - use the correct field name from new backend
  const cpuUsage = currentMetric?.usage_percent || 0;

  // Extract CPU cores data - cores is now an array of per-core percentages
  const cpuCores = currentMetric?.cores || [];
    
  // Extract top processes data
  const topProcesses = currentMetric?.top_processes || [];

  // Extract CPU details for thermal/details tab
  const cpuDetails: CPUDetails = {
    cores: {
      logical: currentMetric?.logical_cores || 0,
      physical: currentMetric?.physical_cores || 0,
    },
    frequency: {
      current: currentMetric?.frequency_mhz || 0,
      min: currentMetric?.frequency_details?.min || 0,
      max: currentMetric?.frequency_details?.max || 0,
    },
    temperature: currentMetric?.temperature || 0,
    per_core_usage: cpuCores,
    physical_cores: currentMetric?.physical_cores || 0,
  };

  // Debug logging for the new data structure
  console.log('🔧 CPU Component - New backend data structure:');
  console.log('🔧 usage_percent:', currentMetric?.usage_percent);
  console.log('🔧 physical_cores:', currentMetric?.physical_cores);
  console.log('🔧 logical_cores:', currentMetric?.logical_cores);
  console.log('🔧 frequency_mhz:', currentMetric?.frequency_mhz);
  console.log('🔧 temperature:', currentMetric?.temperature);
  console.log('🔧 cores array length:', cpuCores.length);
  console.log('🔧 top_processes length:', topProcesses.length);

  // Extract CPU processes
  const cpuProcesses: CPUProcess[] = topProcesses.map((p: any) => ({
    name: p.name || 'Unknown',
    pid: p.pid || 0,
    cpu_percent: p.cpu_percent || 0,
    memory_percent: p.memory_percent || 0
  }));

  // Chart data
  const chartData = historicalMetrics.map((metric: any) => ({
    timestamp: metric.timestamp,
    usage: metric.cpu_usage || 0
  }));
  
  // Generate core usage data for bar chart
  const coreData = cpuDetails.per_core_usage.map((usage: number, index: number) => ({
    name: `Core ${index + 1}`,
    usage
  }));
  
  // Calculate CPU status
  const getStatus = (usage: number): MetricStatus => {
    if (usage >= 90) return 'critical';
    if (usage >= 70) return 'warning';
    return 'normal';
  };

  // Calculate trend
  const getTrend = (current: number, previous: number): 'up' | 'down' | 'stable' => {
    if (current > previous + 5) return 'up';
    if (current < previous - 5) return 'down';
    return 'stable';
  };

  // Get previous value from historical metrics
  const previousValue = historicalMetrics.length > 1 ? 
    historicalMetrics[historicalMetrics.length - 2].cpu_usage || cpuUsage : 
    cpuUsage;

  // Calculate change percentage (avoid division by zero)
  const changePercentage = previousValue !== 0 ? 
    ((cpuUsage - previousValue) / previousValue) * 100 : 
    0;

  // Render the overview tab
  const renderOverviewTab = () => {
    // If using the dashboard mode, render the dashboard style overview
    if (dashboardMode) {
      return (
        <div className="overview-content">
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3a86ff" stopOpacity={0.8}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis 
                  dataKey="timestamp"
                  tickFormatter={(time: string) => new Date(time).toLocaleTimeString()}
                  stroke="var(--text-secondary)"
                />
                <YAxis 
                  domain={[0, 100]} 
                  tickFormatter={(value: number) => `${value}%`}
                  stroke="var(--text-secondary)"
                />
                <Tooltip 
                  formatter={(value: number) => [`${value.toFixed(1)}%`, 'CPU Usage']}
                  labelFormatter={(label: string) => new Date(label).toLocaleTimeString()}
                  contentStyle={{ 
                    backgroundColor: 'var(--card-bg)', 
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)'
                  }}
                  itemStyle={{ color: 'var(--primary)' }}
                  labelStyle={{ color: 'var(--text-primary)' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="usage" 
                  stroke="var(--primary)" 
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#cpuGradient)"
                  activeDot={{ r: 6, strokeWidth: 0, fill: 'var(--primary)' }}
                  isAnimationActive={true}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      );
    }
    
    // Otherwise use the component style overview tab
    return (
      <CPUOverviewTab data={{
        name: 'CPU',
        temp: {
          current: cpuDetails.temperature,
          min: 0,
          max: 100,
          critical: 90,
          throttle_threshold: 85,
          unit: 'C'
        },
        temperature: {
          current: cpuDetails.temperature,
          min: 0,
          max: 100,
          critical: 90,
          throttle_threshold: 85,
          unit: 'C'
        },
        frequency: {
          current: cpuDetails.frequency.current,
          min: 0,
          max: cpuDetails.frequency.max
        },
        processes: cpuProcesses.map((p: CPUProcess) => ({
          user: 'system',
          command: p.name,
          usage_percent: p.cpu_percent,
          pid: p.pid,
          memory_percent: p.memory_percent
        })),
        top_processes: cpuProcesses.map((p: CPUProcess) => ({
          user: 'system',
          command: p.name,
          usage_percent: p.cpu_percent,
          pid: p.pid,
          memory_percent: p.memory_percent
        })),
        core_count: cpuDetails.cores.physical,
        logical_cores: cpuDetails.cores.logical,
        usage_percent: cpuUsage,
        overall_usage: cpuUsage,
        process_count: cpuProcesses.length,
        thread_count: cpuDetails.cores.logical,
        physical_cores: cpuDetails.cores.physical,
        model_name: currentMetric.cpu_model || 'System CPU',
        frequency_mhz: cpuDetails.frequency.current,
        cores: cpuDetails.per_core_usage.map((usage: number, id: number) => ({
          id,
          usage_percent: usage,
          frequency_mhz: cpuDetails.frequency.current
        })),
        historical_temp: []
      }} compact={compact} />
    );
  };

  // Render the cores tab
  const renderCoresTab = () => {
    // If using the dashboard mode, render the dashboard style cores tab
    if (dashboardMode) {
      return (
        <div className="cores-content">
          <h3>CPU Cores</h3>
          <div className="cores-chart">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={coreData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="usage" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      );
    }
    
    // Otherwise use the component style cores tab
    return (
      <CPUCoresTab 
        cores={cpuDetails.per_core_usage.map((usage: number, id: number) => ({
          id,
          usage_percent: usage
        }))}
        physicalCores={cpuDetails.physical_cores || cpuDetails.per_core_usage.length}
        compact={compact}
      />
    );
  };
  
  // Removed unused renderCoreItem function

  // Render the processes tab
  const renderProcessesTab = () => {
    // If using the dashboard mode, render the dashboard style processes tab
    if (dashboardMode) {
      return (
        <div className="processes-content">
          <h3>Top CPU Processes</h3>
          <div className="process-list">
            {cpuProcesses.length > 0 ? (
              cpuProcesses.map((process: CPUProcess, index: number) => (
                <Card key={index} className="process-card">
                  <div className="process-name">{process.name}</div>
                  <div className="process-usage">{process.cpu_percent.toFixed(1)}%</div>
                  <div className="process-details">
                    <span>PID: {process.pid}</span>
                    <span>Memory: {process.memory_percent.toFixed(1)}%</span>
                  </div>
                </Card>
              ))
            ) : (
              <div className="no-data">No process data available</div>
            )}
          </div>
        </div>
      );
    }
    
    // Otherwise use the component style processes tab
    return (
      <CPUProcessesTab 
        processes={cpuProcesses.map((p: CPUProcess) => ({
          ...p,
          user: 'system',
          command: p.name,
          usage_percent: p.cpu_percent
        }))}
        compact={compact}
      />
    );
  };

  // Render the details/thermal tab
  const renderDetailsTab = () => {
    // If using the dashboard mode, render the dashboard style details tab
    if (dashboardMode) {
      return (
        <div className="details-content">
          <h3>CPU Details</h3>
          <div>
            <div>Temperature: {cpuDetails.temperature ? `${cpuDetails.temperature.toFixed(1)}°C` : 'N/A'}</div>
            <div>Frequency: {cpuDetails.frequency.current ? `${(cpuDetails.frequency.current / 1000).toFixed(2)} GHz` : 'N/A'}</div>
            <div>Cores: {cpuDetails.cores.physical || 'N/A'} physical, {cpuDetails.cores.logical || 'N/A'} logical</div>
            <div>Model: {currentMetric.cpu_model || 'N/A'}</div>
          </div>
        </div>
      );
    }
    
    // Otherwise use the component style thermal tab
    return (
      <CPUThermalTab 
        temperature={{
          current: cpuDetails.temperature,
          min: 0,
          max: 100,
          critical: 90,
          throttle_threshold: 85,
          unit: 'C'
        }}
        historicalData={[]}
        compact={compact}
      />
    );
  };

  // Render tab content based on active tab
  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return renderOverviewTab();
      case 'cores':
        return renderCoresTab();
      case 'processes':
        return renderProcessesTab();
      case 'thermal':
        return renderDetailsTab();
      default:
        return renderOverviewTab();
    }
  };

  // If dashboard mode, use the dashboard style layout with MetricsCard
  if (dashboardMode) {
    return (
      <div className="cpu-metric" style={{ height }}>
        <MetricsCard
          title="CPU Usage"
          value={`${cpuUsage.toFixed(1)}`}
          unit="%"
          status={getStatus(cpuUsage)}
          trend={getTrend(cpuUsage, previousValue)}
          changePercentage={changePercentage}
          showSparkline={true}
          sparklineData={chartData.map(d => d.usage)}
        >
          {showTabs && (
            <Tabs activeTab={activeTab} onChange={(tabId) => setActiveTab(tabId as CPUTabType)}>
              <Tab id="overview" label="Overview">{renderTabContent()}</Tab>
              <Tab id="cores" label="Cores">{renderTabContent()}</Tab>
              <Tab id="processes" label="Processes">{renderTabContent()}</Tab>
              <Tab id="thermal" label="Details">{renderTabContent()}</Tab>
            </Tabs>
          )}
        </MetricsCard>
      </div>
    );
  }
  
  // Otherwise use the component style layout
  return (
    <div className={`metric-card ${compact ? 'compact' : ''}`} style={{ height }}>
      <h3>CPU Activity</h3>
      
      {showTabs && (
        <div className="cpu-tabs">
          <div 
            className={`cpu-tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </div>
          <div 
            className={`cpu-tab ${activeTab === 'processes' ? 'active' : ''}`}
            onClick={() => setActiveTab('processes')}
          >
            Processes
          </div>
          <div 
            className={`cpu-tab ${activeTab === 'cores' ? 'active' : ''}`}
            onClick={() => setActiveTab('cores')}
          >
            Cores
          </div>
          <div 
            className={`cpu-tab ${activeTab === 'thermal' ? 'active' : ''}`}
            onClick={() => setActiveTab('thermal')}
          >
            Thermal
          </div>
        </div>
      )}
      
      <div className="cpu-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default CPUMetric;