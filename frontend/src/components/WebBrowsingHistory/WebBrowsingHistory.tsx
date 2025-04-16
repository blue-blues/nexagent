import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  TextField,
  InputAdornment,
  Divider,
  Tooltip,
  Chip,
  Collapse,
  Card,
  CardContent
} from '@mui/material';
import {
  Search,
  OpenInNew,
  Bookmark,
  BookmarkBorder,
  ExpandMore,
  ExpandLess,
  History,

} from '@mui/icons-material';
import { WebBrowsingHistoryItem } from '../../types';

interface WebBrowsingHistoryProps {
  conversationId: string;
  historyItems?: WebBrowsingHistoryItem[];
  onOpenUrl?: (url: string) => void;
}

const WebBrowsingHistory: React.FC<WebBrowsingHistoryProps> = ({
  conversationId,
  historyItems = [],
  onOpenUrl
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [bookmarkedItems, setBookmarkedItems] = useState<string[]>([]);
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [filteredItems, setFilteredItems] = useState<WebBrowsingHistoryItem[]>(historyItems);

  // Log when history items change
  useEffect(() => {
    console.log(`WebBrowsingHistory: items updated for ${conversationId}`, {
      itemCount: historyItems.length
    });
  }, [historyItems, conversationId]);

  // Safely access history items with fallback
  const safeHistoryItems = useMemo(() => {
    return historyItems || [];
  }, [historyItems]);

  // Update filtered items when history items or search term changes
  useEffect(() => {
    if (searchTerm) {
      const lowercaseSearch = searchTerm.toLowerCase();
      setFilteredItems(
        safeHistoryItems.filter(
          item =>
            (item.title?.toLowerCase() || '').includes(lowercaseSearch) ||
            (item.url?.toLowerCase() || '').includes(lowercaseSearch)
        )
      );
    } else {
      setFilteredItems(safeHistoryItems);
    }
  }, [safeHistoryItems, searchTerm]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const toggleBookmark = (id: string) => {
    if (bookmarkedItems.includes(id)) {
      setBookmarkedItems(bookmarkedItems.filter(itemId => itemId !== id));
    } else {
      setBookmarkedItems([...bookmarkedItems, id]);
    }
  };

  const toggleExpand = (id: string) => {
    if (expandedItems.includes(id)) {
      setExpandedItems(expandedItems.filter(itemId => itemId !== id));
    } else {
      setExpandedItems([...expandedItems, id]);
    }
  };

  const handleOpenUrl = (url: string) => {
    if (onOpenUrl) {
      onOpenUrl(url);
    } else {
      window.open(url, '_blank');
    }
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <History sx={{ mr: 1 }} />
          Web Browsing History
        </Typography>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search history..."
          value={searchTerm}
          onChange={handleSearchChange}
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        {filteredItems.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No browsing history found
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {filteredItems.map((item, index) => (
              <React.Fragment key={item.id}>
                {index > 0 && <Divider />}
                <ListItem alignItems="flex-start">
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{
                            fontWeight: 'medium',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            mr: 1,
                            flex: 1,
                          }}
                        >
                          {item.title}
                        </Typography>
                        <Chip
                          label={formatTimestamp(item.timestamp)}
                          size="small"
                          variant="outlined"
                          sx={{ ml: 1 }}
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            mb: 0.5,
                          }}
                        >
                          {item.url}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <IconButton
                            size="small"
                            onClick={() => toggleExpand(item.id)}
                            sx={{ mr: 1, p: 0.5 }}
                          >
                            {expandedItems.includes(item.id) ? <ExpandLess /> : <ExpandMore />}
                          </IconButton>
                          <Typography variant="caption" color="text.secondary">
                            {expandedItems.includes(item.id) ? 'Hide preview' : 'Show preview'}
                          </Typography>
                        </Box>
                        <Collapse in={expandedItems.includes(item.id)}>
                          <Card variant="outlined" sx={{ mt: 1, mb: 1 }}>
                            <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                              <Typography variant="body2">
                                {item.preview || 'No preview available'}
                              </Typography>
                            </CardContent>
                          </Card>
                        </Collapse>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="Open in new tab">
                      <IconButton edge="end" onClick={() => handleOpenUrl(item.url)}>
                        <OpenInNew />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={bookmarkedItems.includes(item.id) ? "Remove bookmark" : "Bookmark"}>
                      <IconButton edge="end" onClick={() => toggleBookmark(item.id)}>
                        {bookmarkedItems.includes(item.id) ? <Bookmark color="primary" /> : <BookmarkBorder />}
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        )}
      </Box>
    </Paper>
  );
};

export default WebBrowsingHistory;
