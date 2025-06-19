import { DiskPerformance, DiskHistoryPoint } from '../tabs/types';

interface BottleneckDetectionResult {
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
}

/**
 * Analyzes I/O metrics to detect potential bottlenecks
 */
export const detectIOBottlenecks = (
  performance: DiskPerformance,
  history: DiskHistoryPoint[]
): BottleneckDetectionResult => {
  const result: BottleneckDetectionResult = {
    detected: false,
    type: null,
    severity: null,
    cause: null,
    recommendations: []
  };

  // Check for high utilization
  const isHighUtilization = performance.current.utilization > 85;
  const isModerateUtilization = performance.current.utilization > 70;

  // Check for long queue depth
  const isHighQueueDepth = performance.current.queueDepth > 10;
  const isModerateQueueDepth = performance.current.queueDepth > 4;

  // Check for high latency
  const isHighReadLatency = performance.current.latency.read > 20; // ms
  const isHighWriteLatency = performance.current.latency.write > 20; // ms

  // Check if any metric indicates a bottleneck
  const hasBottleneck = isHighUtilization || isHighQueueDepth || isHighReadLatency || isHighWriteLatency;

  if (!hasBottleneck) {
    return result; // No bottleneck detected
  }

  // We've detected a bottleneck
  result.detected = true;

  // Determine bottleneck type
  if (isHighReadLatency && !isHighWriteLatency) {
    result.type = 'read';
  } else if (isHighWriteLatency && !isHighReadLatency) {
    result.type = 'write';
  } else if (isHighReadLatency && isHighWriteLatency) {
    result.type = 'mixed';
  } else if (isHighUtilization || isHighQueueDepth) {
    // Determine type based on which operation dominates
    const readIOPS = performance.current.readIOPS;
    const writeIOPS = performance.current.writeIOPS;

    if (readIOPS > writeIOPS * 2) {
      result.type = 'read';
    } else if (writeIOPS > readIOPS * 2) {
      result.type = 'write';
    } else {
      result.type = 'mixed';
    }
  }

  // Determine severity
  if (isHighUtilization && isHighQueueDepth && (isHighReadLatency || isHighWriteLatency)) {
    result.severity = 'high';
  } else if (isHighUtilization || isHighQueueDepth) {
    result.severity = 'medium';
  } else if (isModerateUtilization || isModerateQueueDepth) {
    result.severity = 'low';
  }

  // Identify potential cause
  identifyBottleneckCause(result, performance, history);

  // Generate recommendations
  generateIORecommendations(result, performance);

  return result;
};

/**
 * Identifies the most likely cause of a bottleneck
 */
const identifyBottleneckCause = (
  result: BottleneckDetectionResult,
  performance: DiskPerformance,
  history: DiskHistoryPoint[]
): void => {
  // Check for dominant process
  const topProcess = performance.topProcesses[0];
  const secondProcess = performance.topProcesses[1];

  if (topProcess && secondProcess && topProcess.totalRate > secondProcess.totalRate * 3) {
    // One process is using 3x more I/O than the next highest
    result.cause = `Process ${topProcess.name} is dominating I/O operations`;
    result.process = {
      pid: topProcess.pid,
      name: topProcess.name,
      ioRate: topProcess.totalRate
    };
    return;
  }

  // Check for sudden spike in I/O
  if (history.length >= 3) {
    const currentUtil = history[history.length - 1].utilization;
    const prevUtil = history[history.length - 3].utilization;

    if (currentUtil > prevUtil * 2 && currentUtil > 70) {
      result.cause = 'Sudden spike in I/O activity';
      return;
    }
  }

  // Check for sustained high I/O
  if (history.length >= 5) {
    const recentUtils = history.slice(-5).map(h => h.utilization);
    const avgUtil = recentUtils.reduce((sum, val) => sum + val, 0) / recentUtils.length;

    if (avgUtil > 80) {
      result.cause = 'Sustained high I/O activity';
      return;
    }
  }

  // Check type-specific causes
  if (result.type === 'read' && performance.current.readIOPS > 1000) {
    result.cause = 'High number of small read operations';
  } else if (result.type === 'write' && performance.current.writeIOPS > 1000) {
    result.cause = 'High number of small write operations';
  } else if (isHighRandomIO(history)) {
    result.cause = 'High level of random I/O operations';
  } else {
    result.cause = 'General I/O congestion';
  }
};

/**
 * Analyzes I/O patterns to detect if operations are primarily random
 */
const isHighRandomIO = (_history: DiskHistoryPoint[]): boolean => {
  // This would normally analyze actual random vs. sequential I/O metrics
  // For this implementation, we'll use a placeholder
  return false;
};

/**
 * Generates recommendations to address the detected bottleneck
 */
const generateIORecommendations = (
  result: BottleneckDetectionResult,
  _performance: DiskPerformance
): void => {
  const recommendations: string[] = [];

  // Add general recommendation based on severity
  if (result.severity === 'high') {
    recommendations.push(
      'Consider immediate action to reduce I/O pressure on the system.'
    );
  }

  // Add specific recommendations based on type and cause
  if (result.process) {
    recommendations.push(
      `Investigate process ${result.process.name} (PID: ${result.process.pid}) which is responsible for high I/O usage.`
    );

    // Check if it's a known process type
    const processName = result.process.name.toLowerCase();
    if (processName.includes('backup') || processName.includes('sync')) {
      recommendations.push(
        'Consider scheduling backup/sync operations during off-peak hours.'
      );
    } else if (processName.includes('db') || processName.includes('sql')) {
      recommendations.push(
        'Review database queries and indexing to reduce I/O operations.'
      );
    }
  }

  // Recommendations based on bottleneck type
  if (result.type === 'read') {
    recommendations.push(
      'Consider adding more memory for caching frequently read data.'
    );
    recommendations.push(
      'Evaluate application read patterns for optimization opportunities.'
    );
  } else if (result.type === 'write') {
    recommendations.push(
      'Consider enabling write caching if it\'s safe for your workload.'
    );
    recommendations.push(
      'Batch small write operations into larger transactions where possible.'
    );
  }

  // Hardware recommendations for sustained bottlenecks
  if (result.cause === 'Sustained high I/O activity') {
    recommendations.push(
      'Consider upgrading to SSD storage if you\'re currently using spinning disks.'
    );
    recommendations.push(
      'For critical applications, consider adding dedicated disk resources.'
    );
  }

  // Set the recommendations on the result
  result.recommendations = recommendations;
};

export default detectIOBottlenecks;
