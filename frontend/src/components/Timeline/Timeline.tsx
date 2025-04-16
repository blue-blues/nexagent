import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  IconButton,
  Collapse,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Slider

} from '@mui/material';
import {
  Timeline as TimelineIcon,
  ExpandMore,
  ExpandLess,
  FilterList,
  ZoomIn,
  ZoomOut,
  Download,
  Share,
  Edit
} from '@mui/icons-material';
import { TimelineEvent, TimelineData } from '../../types';

interface TimelineProps {
  timelineData: TimelineData;
  conversationId: string;
}

const Timeline: React.FC<TimelineProps> = ({ timelineData, conversationId }) => {
  const [expandedEvents, setExpandedEvents] = useState<string[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [filteredEvents, setFilteredEvents] = useState<TimelineEvent[]>(timelineData?.events || []);
  const timelineRef = useRef<HTMLDivElement>(null);

  // Safely access timeline events with fallback
  const safeEvents = useMemo(() => {
    return timelineData?.events || [];
  }, [timelineData]);

  // Log timeline data changes
  useEffect(() => {
    console.log(`Timeline data updated for ${conversationId}:`, {
      eventCount: safeEvents.length,
      hasData: !!timelineData
    });
  }, [timelineData, conversationId, safeEvents.length]);

  // Update filtered events when timeline data or filter changes
  useEffect(() => {
    if (filterType === 'all') {
      setFilteredEvents(safeEvents);
    } else {
      setFilteredEvents(
        safeEvents.filter(event => event.type === filterType)
      );
    }
  }, [safeEvents, filterType]);

  const toggleEventExpand = (id: string) => {
    if (expandedEvents.includes(id)) {
      setExpandedEvents(expandedEvents.filter(eventId => eventId !== id));
    } else {
      setExpandedEvents([...expandedEvents, id]);
    }
  };

  const handleFilterChange = (event: SelectChangeEvent) => {
    setFilterType(event.target.value);
  };

  const handleZoomChange = (event: Event, newValue: number | number[]) => {
    setZoomLevel(newValue as number);
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  const formatDuration = (startTime: number, endTime?: number) => {
    if (!endTime) return 'In progress...';

    const durationMs = endTime - startTime;
    if (durationMs < 1000) {
      return `${durationMs}ms`;
    } else if (durationMs < 60000) {
      return `${(durationMs / 1000).toFixed(2)}s`;
    } else {
      const minutes = Math.floor(durationMs / 60000);
      const seconds = ((durationMs % 60000) / 1000).toFixed(2);
      return `${minutes}m ${seconds}s`;
    }
  };

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'tool_call':
        return 'primary';
      case 'thinking':
        return 'secondary';
      case 'error':
        return 'error';
      case 'user_input':
        return 'success';
      case 'response':
        return 'info';
      default:
        return 'default';
    }
  };

  const getEventIcon = (event: TimelineEvent) => {
    // This would be replaced with actual icons based on event type
    return <TimelineIcon />;
  };

  const renderEvent = (event: TimelineEvent, depth: number = 0) => {
    // Safety check for invalid events
    if (!event || !event.id) {
      console.warn('Invalid event object received in Timeline', event);
      return null;
    }

    const isExpanded = expandedEvents.includes(event.id);
    const hasChildren = event.children && event.children.length > 0;
    const hasMetadata = event.metadata && Object.keys(event.metadata).length > 0;

    return (
      <React.Fragment key={event.id}>
        <ListItem
          sx={{
            pl: 2 + depth * 3,
            pr: 2,
            py: 1,
            transition: 'all 0.2s',
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }}
        >
          <ListItemIcon sx={{ minWidth: 36 }}>
            {getEventIcon(event)}
          </ListItemIcon>
          <ListItemText
            primary={
              <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontWeight: 'medium',
                    mr: 1,
                  }}
                >
                  {event.name}
                </Typography>
                <Chip
                  label={event.type}
                  size="small"
                  color={getEventTypeColor(event.type)}
                  sx={{ mr: 1 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                  {formatTimestamp(event.start_time)}
                </Typography>
              </Box>
            }
            secondary={
              <Box>
                {event.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {event.description}
                  </Typography>
                )}
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">
                    Duration: {formatDuration(event.start_time, event.end_time)}
                  </Typography>
                  {hasChildren && (
                    <IconButton
                      size="small"
                      onClick={() => toggleEventExpand(event.id)}
                      sx={{ ml: 1, p: 0.5 }}
                    >
                      {isExpanded ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
                    </IconButton>
                  )}
                </Box>
                {event.metadata && Object.keys(event.metadata).length > 0 && (
                  <Box sx={{ mt: 0.5 }}>
                    {Object.entries(event.metadata).map(([key, value]) => (
                      <Typography key={key} variant="caption" display="block" color="text.secondary">
                        <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : value}
                      </Typography>
                    ))}
                  </Box>
                )}
              </Box>
            }
          />
        </ListItem>
        {hasChildren && isExpanded && (
          <Collapse in={isExpanded}>
            {event.children!.map(childEvent => renderEvent(childEvent, depth + 1))}
          </Collapse>
        )}
        <Divider />
      </React.Fragment>
    );
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
            <TimelineIcon sx={{ mr: 1 }} />
            Timeline
          </Typography>
          <Box>
            <Tooltip title="Export timeline">
              <IconButton size="small" sx={{ mr: 1 }}>
                <Download />
              </IconButton>
            </Tooltip>
            <Tooltip title="Share timeline">
              <IconButton size="small" sx={{ mr: 1 }}>
                <Share />
              </IconButton>
            </Tooltip>
            <Tooltip title="Add annotation">
              <IconButton size="small">
                <Edit />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="event-type-filter-label">Event Type</InputLabel>
            <Select
              labelId="event-type-filter-label"
              value={filterType}
              label="Event Type"
              onChange={handleFilterChange}
              size="small"
              startAdornment={<FilterList fontSize="small" sx={{ mr: 0.5 }} />}
            >
              <MenuItem value="all">All Events</MenuItem>
              <MenuItem value="tool_call">Tool Calls</MenuItem>
              <MenuItem value="thinking">Thinking</MenuItem>
              <MenuItem value="error">Errors</MenuItem>
              <MenuItem value="user_input">User Input</MenuItem>
              <MenuItem value="response">Responses</MenuItem>
            </Select>
          </FormControl>
          <Box sx={{ display: 'flex', alignItems: 'center', width: 150 }}>
            <ZoomOut fontSize="small" />
            <Slider
              value={zoomLevel}
              onChange={handleZoomChange}
              min={0.5}
              max={2}
              step={0.1}
              aria-labelledby="zoom-slider"
              sx={{ mx: 1 }}
            />
            <ZoomIn fontSize="small" />
          </Box>
        </Box>
      </Box>

      <Box
        ref={timelineRef}
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          transform: `scale(${zoomLevel})`,
          transformOrigin: 'top left',
          transition: 'transform 0.2s ease-in-out'
        }}
      >
        {filteredEvents.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No timeline events found
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {filteredEvents.map(event => renderEvent(event))}
          </List>
        )}
      </Box>
    </Paper>
  );
};

export default Timeline;
