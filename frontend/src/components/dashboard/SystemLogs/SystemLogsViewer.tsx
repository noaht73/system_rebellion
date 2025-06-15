import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  List, 
  ListItem, 
  Chip, 
  Button, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem,
  IconButton,
  Tooltip,
  CircularProgress,
  Divider
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import InfoIcon from '@mui/icons-material/Info';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import TerminalIcon from '@mui/icons-material/Terminal';
import { format } from 'date-fns';
import systemLogsService, { SystemLog } from '../../../services/systemLogsService';

// Define log level colors and icons
const logLevelConfig = {
  info: { color: 'info', icon: <InfoIcon /> },
  warning: { color: 'warning', icon: <WarningIcon /> },
  error: { color: 'error', icon: <ErrorIcon /> },
  success: { color: 'success', icon: <CheckCircleIcon /> },
  command: { color: 'default', icon: <TerminalIcon /> },
};

// Define source display names
const sourceDisplayNames: Record<string, string> = {
  'auth': 'Authentication',
  'tuner': 'System Tuner',
  'system': 'System',
  'command': 'Command',
  'WebAutoTuner': 'Auto Tuner',
  'MetricsService': 'Metrics Service',
  'LogService': 'Log Service',
  'ResourceMonitor': 'Resource Monitor',
};

interface SystemLogsViewerProps {
  defaultSource?: string;
  defaultLevel?: string;
  maxHeight?: string | number;
  title?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const SystemLogsViewer: React.FC<SystemLogsViewerProps> = ({
  defaultSource,
  defaultLevel,
  maxHeight = 400,
  title = 'System Logs',
  autoRefresh = true,
  refreshInterval = 10000, // 10 seconds
}) => {
  const [logs, setLogs] = useState<SystemLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState<string | undefined>(defaultSource);
  const [level, setLevel] = useState<string | undefined>(defaultLevel);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(100);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await systemLogsService.getLogs(limit, source, level);
      setLogs(response.logs);
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (error) {
      console.error('Error fetching system logs:', error);
    } finally {
      setLoading(false);
    }
  }, [limit, source, level]);

  const handleClearLogs = useCallback(async () => {
    try {
      await systemLogsService.clearLogs();
      fetchLogs();
    } catch (error) {
      console.error('Error clearing logs:', error);
    }
  }, [fetchLogs]);

  // Set up auto-refresh
  useEffect(() => {
    fetchLogs();

    if (autoRefresh) {
      const interval = setInterval(fetchLogs, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [source, level, limit, autoRefresh, refreshInterval]); // eslint-disable-line react-hooks/exhaustive-deps

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'MMM d, yyyy HH:mm:ss');
    } catch (error) {
      return timestamp;
    }
  };

  // Get source display name
  const getSourceDisplayName = (source: string) => {
    return sourceDisplayNames[source] || source;
  };

  return (
    <Paper elevation={3} sx={{ component : "span", height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box component = "span" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2">
          {title} {total > 0 && `(${total})`}
        </Typography>
        <Box component = "span" sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh logs">
            <IconButton onClick={fetchLogs} size="small">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear all logs">
            <IconButton onClick={handleClearLogs} size="small" color="error">
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Box component = "span" sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Source</InputLabel>
          <Select
            value={source || ''}
            label="Source"
            onChange={(e) => setSource(e.target.value === '' ? undefined : e.target.value)}
          >
            <MenuItem value="">All Sources</MenuItem>
            {Object.entries(sourceDisplayNames).map(([key, name]) => (
              <MenuItem key={key} value={key}>{name}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Level</InputLabel>
          <Select
            value={level || ''}
            label="Level"
            onChange={(e) => setLevel(e.target.value === '' ? undefined : e.target.value)}
          >
            <MenuItem value="">All Levels</MenuItem>
            <MenuItem value="info">Info</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="error">Error</MenuItem>
            <MenuItem value="success">Success</MenuItem>
            <MenuItem value="command">Command</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box component = "span" sx={{ flexGrow: 1, overflow: 'auto', maxHeight }}>
        {loading && logs.length === 0 ? (
          <Box component = "span" sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress size={24} sx={{ mr: 1 }} />
            <Typography variant="body2">Loading logs...</Typography>
          </Box>
        ) : logs.length === 0 ? (
          <Box component = "span" sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Typography variant="body2" color="text.secondary">No logs found</Typography>
          </Box>
        ) : (
          <List dense disablePadding>
            {logs.map((log, index) => {
              const levelConfig = logLevelConfig[log.level as keyof typeof logLevelConfig] || logLevelConfig.info;
              
              return (
                <ListItem
                  key={index}
                  divider={index < logs.length - 1}
                  sx={{
                    borderLeft: `4px solid ${levelConfig.color}.main`,
                    mb: 1,
                    backgroundColor: `${levelConfig.color}.lightest`,
                    '&:hover': {
                      backgroundColor: `${levelConfig.color}.lighter`,
                    },
                  }}
                >
                  <Box sx={{ width: '100%', py: 1 }}>
                    {/* Primary content */}
                    <Box component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      {React.cloneElement(levelConfig.icon as React.ReactElement<any>, { 
                        sx: { color: `var(--${levelConfig.color}-main)`, fontSize: '1rem' } 
                      })}
                      <Typography variant="body1" component="div" sx={{ fontWeight: 'medium' }}>
                        {log.message}
                      </Typography>
                    </Box>
                    
                    {/* Secondary content */}
                    <Box component="div" sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Chip
                        label={getSourceDisplayName(log.source)}
                        size="small"
                        variant="outlined"
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                      <Typography variant="body2" color="textSecondary" component="span">
                        {formatTimestamp(log.timestamp)}
                      </Typography>
                    </Box>
                  </Box>
                </ListItem>
              );
            })}
          </List>
        )}
      </Box>

      {hasMore && (
        <Box component = "span" sx={{ mt: 2, textAlign: 'center' }}>
          <Button
            variant="outlined"
            size="small"
            onClick={() => setLimit(prev => prev + 100)}
          >
            Load More
          </Button>
        </Box>
      )}
    </Paper>
  );
};

export default SystemLogsViewer;
