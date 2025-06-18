import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../../../store/hooks';
import { Link } from 'react-router-dom';
import './DashboardNew.css';
import { fetchPatterns } from '../../../store/slices/autoTunerSlice';
import { fetchSystemAlerts } from '../../../store/slices/systemAlertsSlice';
import { useMetricsWebSocket } from '../../../services/websocket/useMetricsWebSocket';
import { RootState } from '../../../store/store';
import SystemStatus from './SystemStatus/SystemStatus';
import CPUMetric from '../../../components/metrics/CPU/CPUMetric';
import MemoryMetric from '../../../components/metrics/memory/MemoryMetric';
import DiskMetric from '../../../components/metrics/disk/DiskMetric';
import NetworkMetric from '../../../components/metrics/Network/NetworkMetric';
import SystemAlertsPanel from '../SystemAlertsPanel/SystemAlertsPanel';
import SystemPatternsPanel from '../SystemPatternsPanel/SystemPatternsPanel';

interface DashboardProps {}

export const DashboardNew: React.FC<DashboardProps> = () => {
  // Get the app dispatch function to dispatch actions
  const dispatch = useAppDispatch();

  // Get the user from the auth state
  const { user } = useAppSelector((state) => state.auth);

  // Get the status and error from the metrics state
  const { status, error } = useAppSelector((state: RootState) => state.metrics);
  
  // Determine if we're loading (connecting and no metrics data)
  const loading = status === 'connecting' && !(
    useAppSelector((state: RootState) => state.metrics.cpuMetrics) ||
    useAppSelector((state: RootState) => state.metrics.memoryMetrics) ||
    useAppSelector((state: RootState) => state.metrics.diskMetrics) ||
    useAppSelector((state: RootState) => state.metrics.networkMetrics)
  );

  // Establish WebSocket connection and get controls
  const { requestSystemInfo, resetCircuitBreaker } = useMetricsWebSocket();
  
  // Fetch initial data
  useEffect(() => {
    // Fetch patterns
    dispatch(fetchPatterns() as any);
    
    // Fetch system alerts
    dispatch(fetchSystemAlerts({ skip: 0, limit: 5 }));
  }, [dispatch]);

  // Display personalized welcome message if user is available
  const getWelcomeMessage = () => {
    if (user?.username) {
      // Get the current hour
      const hour = new Date().getHours();
      
      // Determine the greeting
      const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
      
      // Return the greeting with the username
      return `${greeting}, ${user.username}!`;
    }
    
    // Return the default welcome message
    return "System Dashboard";
  };

  // Check if we have any metrics data
  const {
    cpuMetrics,
    memoryMetrics,
    diskMetrics,
    networkMetrics
  } = useAppSelector((state: RootState) => state.metrics);

  const hasMetricsData = cpuMetrics || memoryMetrics || diskMetrics || networkMetrics;
  
  // Only show loading state if we're connecting AND have no metrics data
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading dashboard metrics...</p>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="error-container">
        <div className="dashboard-header">
          <h1>System Dashboard</h1>
          <div className="connection-controls">
            <div className={`connection-status ${status}`}>
              {status === 'connected' ? ' ' : 
               status === 'error' ? ' ' : 
               ' '}
            </div>
            <button 
              className="circuit-reset-button"
              onClick={resetCircuitBreaker}
              title="Reset the circuit breaker and reconnect"
            >
              Reset Connection
            </button>
            <button 
              className="refresh-button" 
              onClick={requestSystemInfo}
              title="Refresh metrics data"
            >
              Refresh
            </button>
          </div>
        </div>
        <h2> Connection Error</h2>
        <p>{error}</p>
        <div className="error-actions">
          <button 
            className="retry-button"
            onClick={resetCircuitBreaker}
          >
            Reset Circuit Breaker & Reconnect
          </button>
          <button 
            className="retry-button secondary"
            onClick={() => window.location.reload()}
          >
            Reload Page
          </button>
        </div>
        <p className="error-help-text">If the circuit breaker is open, try resetting it first.</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>{getWelcomeMessage()}</h1>
        <div className="connection-controls">
          <div className={`connection-status ${status}`}>
            {status === 'connected' ? ' ' : 
             status === 'error' ? ' ' : 
             ' '}
          </div>
          <button 
            className="circuit-reset-button"
            onClick={resetCircuitBreaker}
            title="Reset the circuit breaker and reconnect"
          >
            Reset Connection
          </button>
          <button 
            className="refresh-button" 
            onClick={requestSystemInfo}
            title="Refresh metrics data"
          >
            Refresh
          </button>
        </div>
      </div>
      
      <div className="dashboard-metrics">
        <div className="metrics-header">
          <h2>System Metrics</h2>
          <Link to="/metrics" className="section-link" replace>View All Metrics</Link>
        </div>
        
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-card-header">
              <h3>CPU Usage</h3>
              <Link to="/metrics" state={{ section: 'cpu' }} className="metric-link" replace>Details</Link>
            </div>
            <CPUMetric />
          </div>
          
          <div className="metric-card">
            <div className="metric-card-header">
              <h3>Memory Usage</h3>
              <Link to="/metrics" state={{ section: 'memory' }} className="metric-link" replace>Details</Link>
            </div>
            <MemoryMetric />
          </div>
          
          <div className="metric-card">
            <div className="metric-card-header">
              <h3>Disk Usage</h3>
              <Link to="/metrics" state={{ section: 'disk' }} className="metric-link" replace>Details</Link>
            </div>
            <DiskMetric />
          </div>
          
          <div className="metric-card">
            <div className="metric-card-header">
              <h3>Network Traffic</h3>
              <Link to="/metrics" state={{ section: 'network' }} className="metric-link" replace>Details</Link>
            </div>
            <NetworkMetric />
          </div>
        </div>
      </div>
      
      <div className="sidebar-panel alerts-panel">
        <div className="panel-header">
          <h2>System Alerts</h2>
          <Link to="/alerts" className="section-link" replace>View All Alerts</Link>
        </div>
        <SystemAlertsPanel maxAlerts={5} showAllLink={false} />
      </div>
      
      <div className="sidebar-panel patterns-panel">
        <div className="panel-header">
          <h2>System Patterns</h2>
          <Link to="/auto-tuner" className="section-link" replace>View All Patterns</Link>
        </div>
        <SystemPatternsPanel maxPatterns={5} />
      </div>
    </div>
  );
};

export default DashboardNew;
