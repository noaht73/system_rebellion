export interface DiskMetricProps {
  compact?: boolean;
  defaultTab?: 'partitions' | 'directory' | 'performance';
}

// Raw disk data from Redux store
export interface RawDiskMetrics {
  // Partition data
  partitions: DiskPartition[];
  // Physical disk data
  physicalDisks: PhysicalDisk[];
  // Directory size data
  directories: DirectoryInfo[];
  // I/O Performance data
  performance: DiskPerformance;
  // Historical I/O data
  history: DiskHistoryPoint[];
}

export interface DiskPartition {
  mountPoint: string;       // Mount point (e.g., "/", "/home")
  device: string;           // Device name (e.g., "/dev/sda1")
  fsType: string;           // Filesystem type (e.g., "ext4", "ntfs")
  total: number;            // Total space in bytes
  used: number;             // Used space in bytes
  available: number;        // Available space in bytes
  percentUsed: number;      // Percentage used (0-100)
  inodes: {                 // Inode usage (Unix filesystems)
    total: number;
    used: number;
    free: number;
    percentUsed: number;
  };
  health: {                 // Filesystem health metrics
    errors: number;
    lastCheckTime: number;
    status: 'healthy' | 'warning' | 'error';
    issues: string[];
  };
  readOnly: boolean;        // Is the filesystem mounted read-only
  physicalDiskId: string;   // Reference to the physical disk
}

export interface PhysicalDisk {
  id: string;               // Disk identifier
  model: string;            // Disk model
  serial: string;           // Serial number
  type: 'ssd' | 'hdd' | 'nvme' | 'other'; // Disk type
  size: number;             // Size in bytes
  interface: string;        // Interface type (SATA, NVMe, etc.)
  temperature: number;      // Temperature in celsius
  smart: SmartData;         // SMART data
  partitions: string[];     // References to partitions on this disk
}

export interface SmartData {
  status: 'passed' | 'warning' | 'failed'; // Overall SMART status
  attributes: {
    id: number;             // Attribute ID
    name: string;           // Attribute name
    value: number;          // Current value
    worst: number;          // Worst value
    threshold: number;      // Threshold value
    raw: number;            // Raw value
    status: 'good' | 'warning' | 'bad'; // Status based on threshold
  }[];
  lifeRemaining: number;    // Estimated life remaining (percentage)
  healthAssessment: string; // Human-readable health assessment
}

export interface DirectoryInfo {
  path: string;             // Full path
  size: number;             // Size in bytes
  fileCount: number;        // Number of files
  subdirectoryCount: number; // Number of subdirectories
  lastModified: number;     // Last modified timestamp
  children?: DirectoryInfo[]; // Subdirectories (for treemap)
  usage?: {                 // Usage categorization (for cleanup recommendations)
    type: 'system' | 'application' | 'user' | 'cache' | 'temp' | 'other';
    cleanable: boolean;     // Can be safely cleaned
    lastAccessed: number;   // Last accessed timestamp
  };
}

export interface DiskPerformance {
  current: {
    readSpeed: number;      // Current read speed in bytes/sec
    writeSpeed: number;     // Current write speed in bytes/sec
    readIOPS: number;       // Read operations per second
    writeIOPS: number;      // Write operations per second
    utilization: number;    // Disk utilization percentage (0-100)
    queueDepth: number;     // Current queue depth
    latency: {              // Access latency
      read: number;         // Read latency in ms
      write: number;        // Write latency in ms
    };
  };
  bottlenecks: {
    detected: boolean;      // Is a bottleneck detected
    type: 'read' | 'write' | 'mixed' | null; // Bottleneck type
    severity: 'low' | 'medium' | 'high' | null; // Bottleneck severity
    cause: string | null;   // Probable cause
    process?: {             // Process causing bottleneck (if identified)
      pid: number;
      name: string;
      ioRate: number;       // I/O rate in bytes/sec
    };
    recommendations: string[]; // Recommendations to address bottleneck
  };
  topProcesses: {           // Top I/O consuming processes
    pid: number;
    name: string;
    readRate: number;       // Read rate in bytes/sec
    writeRate: number;      // Write rate in bytes/sec
    totalRate: number;      // Total I/O rate in bytes/sec
    iops: number;           // Total IOPS
  }[];
}

export interface DiskHistoryPoint {
  timestamp: number;
  readSpeed: number;
  writeSpeed: number;
  readIOPS: number;
  writeIOPS: number;
  utilization: number;
  topProcesses: {
    pid: number;
    totalRate: number;
  }[];
}

// Processed data structure for components
export interface ProcessedDiskData {
  partitions: {
    items: {
      blockSize: any;
      mountPoint: string;
      device: string;
      fsType: string;
      total: number;
      used: number;
      available: number;
      percentUsed: number;
      health: {
        status: 'healthy' | 'warning' | 'error';
        issues: string[];
      };
      inodeUsage: number;
      readOnly: boolean;
      physicalDiskId: string;
      uniqueId: string; // Added unique identifier field
    }[];
    totalDiskSpace: number;
    usedDiskSpace: number;
    overallHealth: 'healthy' | 'warning' | 'error';
  };
  physicalDisks: {
    items: {
      id: string;
      model: string;
      type: 'ssd' | 'hdd' | 'nvme' | 'other';
      size: number;
      temperature: number;
      health: {
        status: 'passed' | 'warning' | 'failed';
        lifeRemaining: number;
        issues: string[];
      };
      partitions: string[];
    }[];
    overallHealth: 'good' | 'warning' | 'critical';
    criticalIssues: {
      diskId: string;
      issue: string;
    }[];
  };
  directories: {
    largest: {
      path: string;
      size: number;
      fileCount: number;
      lastModified: number;
      type: string;
      cleanable: boolean;
    }[];
    treemapData: {
      name: string;
      path: string;
      value: number;
      children?: any[];
    };
    cleanupRecommendations: {
      id: string;
      path: string;
      size: number;
      description: string;
      impact: 'high' | 'medium' | 'low';
      action: string;
    }[];
    totalAnalyzedSize: number;
  };
  performance: {
    current: {
      readSpeed: number;
      writeSpeed: number;
      readIOPS: number;
      writeIOPS: number;
      utilization: number;
      latency: {
        read: number;
        write: number;
      };
    };
    historical: {
      timestamps: number[];
      readSpeed: number[];
      writeSpeed: number[];
      readIOPS: number[];
      writeIOPS: number[];
      utilization: number[];
    };
    topProcesses: {
      pid: number;
      name: string;
      readRate: number;
      writeRate: number;
      totalRate: number;
      percentage: number;
    }[];
    bottlenecks: {
      detected: boolean;
      type: 'read' | 'write' | 'mixed' | null;
      severity: 'low' | 'medium' | 'high' | null;
      cause: string | null;
      process?: {
        pid: number;
        name: string;
        ioRate: number;
      };
      recommendations: string[];
    };
  };
}
