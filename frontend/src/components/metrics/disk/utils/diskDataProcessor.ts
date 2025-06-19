import { RawDiskMetrics, ProcessedDiskData } from '../tabs/types';
import { analyzeSmartData } from './smartDataAnalyzer';
import { generateCleanupRecommendations } from './diskCleanupEngine';
import { detectIOBottlenecks } from './iobottleneckDetector';

/**
 * Processes raw disk metrics into structured data for components
 */
export const processDiskData = (
  rawData: RawDiskMetrics
): ProcessedDiskData => {
  // Process partition data
  const partitions = processPartitionsData(rawData);
  
  // Process physical disk data
  const physicalDisks = processPhysicalDisksData(rawData);
  
  // Process directory data
  const directories = processDirectoryData(rawData);
  
  // Process performance data
  const performance = processPerformanceData(rawData);
  
  return {
    partitions,
    physicalDisks,
    directories,
    performance
  };
};

/**
 * Process partition-related data
 */
const processPartitionsData = (rawData: RawDiskMetrics): ProcessedDiskData['partitions'] => {
  const partitionItems = rawData.partitions.map((partition: any) => {
    // Create safe defaults for potentially missing properties
    const health = partition.health || { status: 'healthy', issues: [] };
    const inodes = partition.inodes || { percentUsed: 0 };
    
    // Generate a unique ID for partitions with 'Unknown' mountPoint
    const uniqueId = `partition-${Math.random().toString(36).substring(2, 9)}`;
    
    return {
      blockSize: partition.blockSize ?? 0,
      mountPoint: partition.mountPoint || `Unknown-${uniqueId}`,
      device: partition.device || 'Unknown',
      fsType: partition.fsType || 'Unknown',
      uniqueId: partition.mountPoint || uniqueId, // Add a guaranteed unique ID
      total: partition.total || 0,
      used: partition.used || 0,
      available: partition.available || 0,
      percentUsed: partition.percentUsed || 0,
      health: {
        status: health.status || 'healthy',
        issues: health.issues || []
      },
      inodeUsage: inodes.percentUsed || 0,
      readOnly: partition.readOnly || false,
      physicalDiskId: partition.physicalDiskId || ''
    };
  });
  
  // Calculate total and used disk space across all partitions
  const totalDiskSpace = partitionItems.reduce((total: any, partition: { total: any; }) => total + partition.total, 0);
  const usedDiskSpace = partitionItems.reduce((total: any, partition: { used: any; }) => total + partition.used, 0);
  
  // Determine overall health
  const healthStatuses = partitionItems.map((p: { health: { status: any; }; }) => p.health.status);
  const overallHealth = healthStatuses.includes('error') 
    ? 'error' 
    : healthStatuses.includes('warning')
      ? 'warning'
      : 'healthy';
  
  return {
    items: partitionItems,
    totalDiskSpace,
    usedDiskSpace,
    overallHealth
  };
};

/**
 * Process physical disk data including SMART analysis
 */
const processPhysicalDisksData = (rawData: RawDiskMetrics): ProcessedDiskData['physicalDisks'] => {
  // Process physical disk items with SMART analysis
  const diskItems = rawData.physicalDisks.map((disk: any) => {
    // Create safe defaults for potentially missing properties
    const smart = disk.smart || { status: 'passed', lifeRemaining: 100, attributes: [] };
    
    // Analyze SMART data for health assessment with fallback
    const smartAnalysis = smart.attributes ? analyzeSmartData(smart) : { issues: [] };
    
    // Ensure disk ID is always unique
    const uniqueId = `disk-${Math.random().toString(36).substring(2, 9)}`;
    
    return {
      id: disk.id || uniqueId,
      model: disk.model || 'Unknown Disk',
      type: disk.type || 'other',
      size: disk.size || 0,
      temperature: disk.temperature || 0,
      health: {
        status: smart.status || 'passed',
        lifeRemaining: smart.lifeRemaining || 100,
        issues: smartAnalysis.issues || []
      },
      partitions: disk.partitions || []
    };
  });
  
  // Extract critical issues across all disks
  const criticalIssues = diskItems.flatMap((disk: { health: { issues: any[]; }; id: any; }) => 
    disk.health.issues.map((issue: any) => ({
      diskId: disk.id,
      issue
    }))
  );
  
  // Determine overall health
  const healthStatuses = diskItems.map((d: { health: { status: any; }; }) => d.health.status);
  const overallHealth = healthStatuses.includes('failed') 
    ? 'critical' 
    : healthStatuses.includes('warning')
      ? 'warning'
      : 'good';
  
  return {
    items: diskItems,
    overallHealth,
    criticalIssues
  };
};

/**
 * Process directory data and generate cleanup recommendations
 */
const processDirectoryData = (rawData: RawDiskMetrics): ProcessedDiskData['directories'] => {
  // Sort directories by size to get largest ones
  const sortedDirs = [...rawData.directories]
    .sort((a, b) => b.size - a.size);
  
  // Extract largest directories
  const largestDirs = sortedDirs.slice(0, 10).map(dir => ({
    path: dir.path,
    size: dir.size,
    fileCount: dir.fileCount,
    lastModified: dir.lastModified,
    type: dir.usage?.type || 'other',
    cleanable: dir.usage?.cleanable || false
  }));
  
  // Create treemap data structure
  const treemapData = createDirectoryTreemap(rawData.directories);
  
  // Generate cleanup recommendations
  const cleanupRecommendations = generateCleanupRecommendations(rawData.directories);
  
  // Calculate total analyzed size
  const totalAnalyzedSize = rawData.directories.reduce((total: any, dir: { size: any; }) => total + dir.size, 0);
  
  return {
    largest: largestDirs,
    treemapData,
    cleanupRecommendations,
    totalAnalyzedSize
  } as any;
};

/**
 * Create hierarchical treemap data structure from directory information
 */
const createDirectoryTreemap = (directories: RawDiskMetrics['directories']) => {
  // Find root directory
  const rootDirectory = directories.find((dir: { path: string; }) => 
    !directories.some((parent: { path: string; }) => dir.path.startsWith(parent.path + '/') && parent.path !== dir.path)
  );
  
  if (!rootDirectory) {
    return { name: 'No data', path: '', value: 0 };
  }
  
  // Recursively build treemap structure
  return buildTreemapNode(rootDirectory, directories);
};

/**
 * Build a single node for the treemap
 */
const buildTreemapNode = (
  directory: RawDiskMetrics['directories'][0],
  allDirectories: RawDiskMetrics['directories']
) => {
  // Find direct children
  const children = allDirectories.filter((dir: { path: string; }) => 
    dir.path.startsWith(directory.path + '/') &&
    dir.path.split('/').length === directory.path.split('/').length + 1
  );
  
  // Create node
  const node: any = {
    name: directory.path.split('/').pop() || directory.path,
    path: directory.path,
    value: directory.size
  };
  
  // Add children if they exist
  if (children.length > 0) {
    node.children = children.map((child: any) => buildTreemapNode(child, allDirectories));
  }
  
  return node;
};

/**
 * Process I/O performance data
 */
const processPerformanceData = (rawData: RawDiskMetrics): ProcessedDiskData['performance'] => {
  // Create safe defaults for potentially missing properties
  const performanceCurrent = rawData.performance?.current || {
    readSpeed: 0,
    writeSpeed: 0,
    readIOPS: 0,
    writeIOPS: 0,
    utilization: 0,
    queueDepth: 0,
    latency: { read: 0, write: 0 }
  };
  
  // Get current performance metrics with safe fallbacks
  const current = {
    readSpeed: performanceCurrent.readSpeed || 0,
    writeSpeed: performanceCurrent.writeSpeed || 0,
    readIOPS: performanceCurrent.readIOPS || 0,
    writeIOPS: performanceCurrent.writeIOPS || 0,
    utilization: performanceCurrent.utilization || 0,
    queueDepth: performanceCurrent.queueDepth || 0,
    latency: {
      read: performanceCurrent.latency?.read || 0,
      write: performanceCurrent.latency?.write || 0
    }
  };
  
  // Process historical data with safe fallback
  const historical = Array.isArray(rawData.history) ? processHistoricalData(rawData.history) : {
    timestamps: [],
    readSpeed: [],
    writeSpeed: [],
    readIOPS: [],
    writeIOPS: [],
    utilization: [],
    queueDepth: [],
    latency: { read: [], write: [] }
  };
  
  // Process top I/O processes with safe fallbacks
  const topProcessesData = rawData.performance?.topProcesses || [];
  const topProcesses = topProcessesData.map((process: any) => {
    const pid = process?.pid || 0;
    const name = process?.name || 'Unknown';
    const readRate = process?.readRate || 0;
    const writeRate = process?.writeRate || 0;
    const totalRate = process?.totalRate || 0;
    
    // Calculate percentage safely
    const totalIoRate = topProcessesData.reduce((sum: number, p: any) => sum + (p?.totalRate || 0), 0);
    const percentage = totalIoRate > 0 ? (totalRate / totalIoRate) * 100 : 0;
    
    return {
      pid,
      name,
      readRate,
      writeRate,
      totalRate,
      percentage
    };
  });
  
  // Detect I/O bottlenecks with safe fallbacks
  const bottlenecks = rawData.performance ? 
    detectIOBottlenecks(rawData.performance, Array.isArray(rawData.history) ? rawData.history : []) : 
    {
      detected: false,
      type: null,
      severity: null,
      cause: null,
      recommendations: []
    };
  
  return {
    current,
    historical,
    topProcesses,
    bottlenecks
  };
};

/**
 * Process historical I/O data into a format suitable for charts
 */
const processHistoricalData = (history: RawDiskMetrics['history']) => {
  // Extract timestamp and metric arrays for charting
  const timestamps = history.map((point: { timestamp: any; }) => point.timestamp);
  const readSpeed = history.map((point: { readSpeed: any; }) => point.readSpeed);
  const writeSpeed = history.map((point: { writeSpeed: any; }) => point.writeSpeed);
  const readIOPS = history.map((point: { readIOPS: any; }) => point.readIOPS);
  const writeIOPS = history.map((point: { writeIOPS: any; }) => point.writeIOPS);
  const utilization = history.map((point: { utilization: any; }) => point.utilization);
  
  return {
    timestamps,
    readSpeed,
    writeSpeed,
    readIOPS,
    writeIOPS,
    utilization
  };
};

export default processDiskData;