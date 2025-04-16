import React, { useState, useEffect } from 'react';
import {
  Alert,
  Box,
  CssBaseline,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  Divider,
  IconButton,
  Button,
  TextField,
  Paper,

  Avatar,
  Badge,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  Snackbar
} from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import {
  Menu as MenuIcon,
  Send,
  Settings,
  Notifications,
  Help,
  Logout,
  Person,
  DarkMode,
  ExpandMore,
  ExpandLess
} from '@mui/icons-material';
import theme from '../../styles/theme';
import ConversationList from '../ConversationManagement/ConversationList';
import TerminalEditor from '../Terminal/TerminalEditor';
import WebBrowsingHistory from '../WebBrowsingHistory/WebBrowsingHistory';
import CodeSnippetLibrary from '../CodeSnippetLibrary/CodeSnippetLibrary';
import ThinkingProcess from '../ThinkingProcess/ThinkingProcess';
import Timeline from '../Timeline/Timeline';
import { Conversation, Message, TimelineData, ThinkingProcessStep } from '../../types';
import * as api from '../../api/api';

const drawerWidth = 280;

interface MainLayoutProps {
  children?: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [processingLongRequest, setProcessingLongRequest] = useState(false);
  const [processingStartTime, setProcessingStartTime] = useState<number | null>(null);
  const [timelineData, setTimelineData] = useState<TimelineData>({ events: [], event_count: 0 });
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingProcessStep[]>([]);
  const [userMenuAnchorEl, setUserMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [expandedSections, setExpandedSections] = useState<string[]>(['terminal', 'thinking', 'timeline']);

  // State for mock mode notification
  const [mockModeAlert, setMockModeAlert] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'available' | 'unavailable'>('available');

  // State for processing time display
  const [processingTimeDisplay, setProcessingTimeDisplay] = useState<string>('');

  // WebSocket for timeline updates
  const [timelineWebSocket, setTimelineWebSocket] = useState<WebSocket | null>(null);

  // Track the last time we logged a status check to reduce log spam
  const [lastStatusCheckLogTime, setLastStatusCheckLogTime] = useState(0);
  const [lastStatusState, setLastStatusState] = useState<boolean | null>(null);

  // Function to check backend status
  const checkBackendStatus = async () => {
    try {
      const now = Date.now();
      const shouldLog = now - lastStatusCheckLogTime > 60000; // Only log once per minute

      if (shouldLog) {
        console.log('Checking backend status from MainLayout...');
      }

      // Use the API's checkBackendAvailability function instead of duplicating code
      const isAvailable = await api.checkBackendAvailability();
      const statusChanged = lastStatusState !== isAvailable;

      // Only log if status changed or it's been a while since last log
      if (shouldLog || statusChanged) {
        console.log('Backend availability check result:', isAvailable);
        setLastStatusCheckLogTime(now);
        setLastStatusState(isAvailable);
      }

      if (isAvailable) {
        if (shouldLog || statusChanged) {
          console.log('Backend is available, updating UI');
        }
        setBackendStatus('available');
        setMockModeAlert(false);
        return true;
      } else {
        if (shouldLog || statusChanged) {
          console.warn('Backend is not available, updating UI');
        }
        setBackendStatus('unavailable');
        setMockModeAlert(true);
        return false;
      }
    } catch (error) {
      const err = error as Error;
      console.error('Error checking backend status:', err);
      setBackendStatus('unavailable');
      setMockModeAlert(true);
      return false;
    }
  };

  // Update processing time display
  useEffect(() => {
    if (processingLongRequest && processingStartTime) {
      const intervalId = setInterval(() => {
        const elapsedSeconds = Math.floor((Date.now() - processingStartTime) / 1000);
        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = elapsedSeconds % 60;
        setProcessingTimeDisplay(
          `${minutes > 0 ? `${minutes} minute${minutes !== 1 ? 's' : ''} and ` : ''}${seconds} second${seconds !== 1 ? 's' : ''}`
        );
      }, 1000);

      return () => clearInterval(intervalId);
    }
  }, [processingLongRequest, processingStartTime]);

  // Load conversations on mount
  useEffect(() => {
    const loadConversations = async () => {
      try {
        // Show loading state
        setLoading(true);

        // Check backend status
        await checkBackendStatus();

        // Get conversations from API
        const data = await api.getConversations();
        setConversations(data);

        // Set active conversation to the most recent one if available
        if (data.length > 0) {
          const mostRecent = data.reduce((prev: Conversation, current: Conversation) =>
            (current.updated_at > prev.updated_at) ? current : prev
          );
          setActiveConversation(mostRecent);
          loadTimelineData(mostRecent.id);
        } else {
          // If no conversations exist, create a new one
          const newConversation: Conversation = {
            id: `new-${Date.now()}`,
            title: 'New Conversation',
            messages: [],
            created_at: Date.now(),
            updated_at: Date.now()
          };

          setConversations([newConversation]);
          setActiveConversation(newConversation);
          setTimelineData({ events: [], event_count: 0 });
        }
      } catch (error) {
        console.error('Error loading conversations:', error);
        // If there's an error, create a new conversation anyway
        const newConversation: Conversation = {
          id: `new-${Date.now()}`,
          title: 'New Conversation',
          messages: [],
          created_at: Date.now(),
          updated_at: Date.now()
        };

        setConversations([newConversation]);
        setActiveConversation(newConversation);
        setTimelineData({ events: [], event_count: 0 });

        // Show mock mode alert
        setMockModeAlert(true);
        setBackendStatus('unavailable');
      } finally {
        setLoading(false);
      }
    };

    loadConversations();

    // Set up periodic backend status check
    const statusCheckInterval = setInterval(() => {
      checkBackendStatus();
    }, 120000); // Check every 120 seconds (reduced from 30 seconds to reduce server load)

    return () => {
      clearInterval(statusCheckInterval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Set up WebSocket connection when active conversation changes
  useEffect(() => {
    let wsInstance: WebSocket | null = null;
    let reconnectTimeout: number | null = null;

    const setupWebSocket = async () => {
      if (activeConversation) {
        // Clear any pending reconnect timeouts
        if (reconnectTimeout) {
          window.clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }

        // Close previous WebSocket if exists
        if (timelineWebSocket) {
          try {
            if (timelineWebSocket.readyState === WebSocket.OPEN ||
                timelineWebSocket.readyState === WebSocket.CONNECTING) {
              timelineWebSocket.close();
            }
          } catch (error) {
            console.error('Error closing previous WebSocket:', error);
          }
        }

        try {
          console.log(`Setting up WebSocket for conversation ${activeConversation.id}`);
          // Check backend status before creating WebSocket
          console.log('Checking backend status before creating WebSocket...');
          const isBackendAvailable = await checkBackendStatus();

          if (!isBackendAvailable) {
            console.warn('Backend is not available, will retry in 8 seconds');
            // Update UI to show mock mode
            setBackendStatus('unavailable');
            setMockModeAlert(true);
            reconnectTimeout = window.setTimeout(setupWebSocket, 8000); // Increased from 5 to 8 seconds
            return;
          }

          // Backend is available, update UI
          console.log('Backend is available, creating WebSocket connection');
          setBackendStatus('available');
          setMockModeAlert(false);

          // Create new WebSocket connection (async)
          const ws = await api.createTimelineWebSocket(activeConversation.id, handleTimelineUpdate);
          wsInstance = ws;
          setTimelineWebSocket(ws);

          // Set up a reconnection mechanism if the WebSocket closes unexpectedly
          ws.addEventListener('close', (event: CloseEvent) => {
            // Only attempt to reconnect if this is still the active WebSocket
            if (wsInstance === ws) {
              if (event.code !== 1000 && event.code !== 1001) {
                console.log(`WebSocket closed unexpectedly with code ${event.code}, scheduling reconnect...`);
                // Use a longer timeout to reduce reconnection frequency
                reconnectTimeout = window.setTimeout(setupWebSocket, 8000); // Increased from 5 to 8 seconds
              } else {
                console.log(`WebSocket closed normally with code ${event.code}`);
              }
            }
          });
        } catch (error) {
          console.error('Error creating WebSocket connection:', error);
          // Schedule a retry
          reconnectTimeout = window.setTimeout(setupWebSocket, 8000); // Increased from 5 to 8 seconds
        }
      }
    };

    setupWebSocket();

    // Clean up WebSocket on unmount or when active conversation changes
    return () => {
      // Clear any pending reconnect timeouts
      if (reconnectTimeout) {
        window.clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }

      // Close the WebSocket if it exists
      if (wsInstance) {
        try {
          if (wsInstance.readyState === WebSocket.OPEN ||
              wsInstance.readyState === WebSocket.CONNECTING) {
            wsInstance.close();
          }
        } catch (error) {
          console.error('Error closing WebSocket during cleanup:', error);
        }
        wsInstance = null;
      }
    };
    // We need activeConversation in the dependency array
    // to properly clean up and recreate the WebSocket when it changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConversation?.id]);

  const handleTimelineUpdate = (data: any) => {
    if (data.type === 'timeline_update') {
      setTimelineData(data.timeline);

      // Extract thinking steps from timeline data if available
      if (data.timeline.events) {
        const thinkingEvents = data.timeline.events.filter((event: any) => event.type === 'thinking');
        const steps: ThinkingProcessStep[] = thinkingEvents.map((event: any, index: number) => ({
          id: event.id,
          step: index + 1,
          description: event.name,
          reasoning: event.description || 'No reasoning provided',
          confidence: event.metadata?.confidence || 0.7,
          alternatives: event.metadata?.alternatives,
          references: event.metadata?.references,
          timestamp: event.start_time
        }));
        setThinkingSteps(steps);
      }
    }
  };

  const loadTimelineData = async (conversationId: string) => {
    try {
      const data = await api.getConversationTimeline(conversationId);
      setTimelineData(data);

      // Extract thinking steps from timeline data if available
      if (data.events) {
        const thinkingEvents = data.events.filter((event: any) => event.type === 'thinking');
        const steps: ThinkingProcessStep[] = thinkingEvents.map((event: any, index: number) => ({
          id: event.id,
          step: index + 1,
          description: event.name,
          reasoning: event.description || 'No reasoning provided',
          confidence: event.metadata?.confidence || 0.7,
          alternatives: event.metadata?.alternatives,
          references: event.metadata?.references,
          timestamp: event.start_time
        }));
        setThinkingSteps(steps);
      }
    } catch (error) {
      console.error('Error loading timeline data:', error);
    }
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleSelectConversation = async (conversationId: string) => {
    try {
      const conversation = await api.getConversation(conversationId);
      setActiveConversation(conversation);
      loadTimelineData(conversationId);
    } catch (error) {
      console.error('Error loading conversation:', error);
    }
  };

  const handleNewConversation = () => {
    // Create a new empty conversation
    const newConversation: Conversation = {
      id: `new-${Date.now()}`,
      title: 'New Conversation',
      messages: [],
      created_at: Date.now(),
      updated_at: Date.now()
    };

    setConversations([newConversation, ...conversations]);
    setActiveConversation(newConversation);
    setTimelineData({ events: [], event_count: 0 });
    setThinkingSteps([]);
  };

  const handleDeleteConversation = (conversationId: string) => {
    // Remove conversation from list
    const updatedConversations = conversations.filter(c => c.id !== conversationId);
    setConversations(updatedConversations);

    // If active conversation was deleted, set active to the most recent one
    if (activeConversation?.id === conversationId) {
      if (updatedConversations.length > 0) {
        const mostRecent = updatedConversations.reduce((prev, current) =>
          (current.updated_at > prev.updated_at) ? current : prev
        );
        setActiveConversation(mostRecent);
        loadTimelineData(mostRecent.id);
      } else {
        setActiveConversation(null);
        setTimelineData({ events: [], event_count: 0 });
        setThinkingSteps([]);
      }
    }
  };

  const handleRenameConversation = (conversationId: string, newTitle: string) => {
    // Update conversation title
    const updatedConversations = conversations.map(c =>
      c.id === conversationId ? { ...c, title: newTitle } : c
    );
    setConversations(updatedConversations);

    // Update active conversation if it was renamed
    if (activeConversation?.id === conversationId) {
      setActiveConversation({ ...activeConversation, title: newTitle });
    }
  };

  const handleMessageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setMessage(e.target.value);
  };

  const handleMessageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !activeConversation) return;

    // Add user message to conversation
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: Date.now()
    };

    const updatedMessages = [...activeConversation.messages, userMessage];
    const updatedConversation = {
      ...activeConversation,
      messages: updatedMessages,
      updated_at: Date.now()
    };

    // Update title based on first message if it's a new conversation
    const newTitle = updatedConversation.messages.length <= 1 ?
      userMessage.content.substring(0, 30) + (userMessage.content.length > 30 ? '...' : '') :
      updatedConversation.title;

    const conversationWithTitle = {
      ...updatedConversation,
      title: newTitle
    };

    setActiveConversation(conversationWithTitle);
    setConversations(conversations.map(c =>
      c.id === activeConversation.id ? conversationWithTitle : c
    ));

    // Clear input
    setMessage('');
    setLoading(true);
    setProcessingLongRequest(false);
    setProcessingStartTime(Date.now());

    // Set a timeout to show long processing message if the request takes more than 15 seconds
    const longRequestTimeout = setTimeout(() => {
      if (loading) {
        setProcessingLongRequest(true);
      }
    }, 15000);

    try {
      // Send message to API
      const response = await api.sendMessage(
        userMessage.content,
        activeConversation.id
      );

      // Add assistant message to conversation
      const assistantMessage: Message = {
        id: response.id,
        role: 'assistant',
        content: response.content,
        timestamp: response.timestamp,
        timeline: response.timeline
      };

      const finalMessages = [...updatedMessages, assistantMessage];
      const finalConversation = {
        ...conversationWithTitle,
        messages: finalMessages,
        updated_at: response.timestamp
      };

      setActiveConversation(finalConversation);
      setConversations(prevConversations =>
        prevConversations.map(c =>
          c.id === activeConversation.id ? finalConversation : c
        )
      );

      // Update timeline data if available
      if (response.timeline) {
        setTimelineData(response.timeline);
      }

      // Handle different types of responses
      if (response.id.startsWith('error-')) {
        console.warn('Received error response from API');
        // Error already handled by the API layer
      } else if (response.id.startsWith('processing-')) {
        console.warn('Received processing response from API');
        // This is a timeout response, but the backend is still working
        // We'll keep the loading state visible to indicate processing
        setLoading(true);

        // Set a timeout to check again after a delay
        setTimeout(() => {
          console.log('Checking if processing is complete...');
          setLoading(false);
        }, 30000); // Check again after 30 seconds
      }
    } catch (error) {
      console.error('Error sending message:', error);

      // This catch block should rarely be hit since our sendMessage function
      // already handles errors and returns a valid Message object
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        timestamp: Date.now()
      };

      const finalMessages = [...updatedMessages, errorMessage];
      const finalConversation = {
        ...conversationWithTitle,
        messages: finalMessages,
        updated_at: Date.now()
      };

      setActiveConversation(finalConversation);
      setConversations(prevConversations =>
        prevConversations.map(c =>
          c.id === activeConversation.id ? finalConversation : c
        )
      );
    } finally {
      // Clear the timeout to prevent state updates after component unmount
      clearTimeout(longRequestTimeout);

      // Only reset loading state if this isn't a long-running request that's still processing
      if (!processingLongRequest) {
        setLoading(false);
        setProcessingLongRequest(false);
        setProcessingStartTime(null);
      }
    }
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchorEl(null);
  };

  const toggleSectionExpand = (section: string) => {
    if (expandedSections.includes(section)) {
      setExpandedSections(expandedSections.filter(s => s !== section));
    } else {
      setExpandedSections([...expandedSections, section]);
    }
  };

  const drawer = (
    <Box sx={{ overflow: 'auto' }}>
      <Toolbar sx={{ justifyContent: 'center' }}>
        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold' }}>
          Nexagent
        </Typography>
      </Toolbar>
      <Divider />
      <Box sx={{ height: 'calc(100vh - 64px)' }}>
        <ConversationList
          conversations={conversations}
          activeConversationId={activeConversation?.id || null}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          onRenameConversation={handleRenameConversation}
        />
      </Box>
    </Box>
  );

  // Handle closing the mock mode alert
  const handleCloseMockAlert = () => {
    setMockModeAlert(false);
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ display: 'flex', height: '100vh' }}>
        <CssBaseline />

        {/* Mock Mode Alert */}
        <Snackbar
          open={mockModeAlert}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
          onClose={handleCloseMockAlert}
        >
          <Alert
            onClose={handleCloseMockAlert}
            severity="warning"
            sx={{ width: '100%' }}
          >
            Backend server is not available. Using mock data instead. Check if the server is running at http://localhost:8000.
          </Alert>
        </Snackbar>
        <AppBar
          position="fixed"
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
              {activeConversation?.title || 'Nexagent'}
            </Typography>
            <Tooltip title="Help">
              <IconButton color="inherit">
                <Help />
              </IconButton>
            </Tooltip>
            <Tooltip title="Notifications">
              <IconButton color="inherit">
                <Badge badgeContent={3} color="error">
                  <Notifications />
                </Badge>
              </IconButton>
            </Tooltip>
            <Tooltip title="Settings">
              <IconButton color="inherit">
                <Settings />
              </IconButton>
            </Tooltip>
            <IconButton
              color="inherit"
              onClick={handleUserMenuOpen}
              sx={{ ml: 1 }}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                <Person />
              </Avatar>
            </IconButton>
          </Toolbar>
        </AppBar>
        <Box
          component="nav"
          sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        >
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{
              keepMounted: true, // Better open performance on mobile.
            }}
            sx={{
              display: { xs: 'block', sm: 'none' },
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
            }}
          >
            {drawer}
          </Drawer>
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: 'none', sm: 'block' },
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
            }}
            open
          >
            {drawer}
          </Drawer>
        </Box>
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          <Toolbar />

          {/* Main content area */}
          <Box sx={{ flexGrow: 1, p: 2, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Chat messages */}
            <Paper
              elevation={0}
              sx={{
                flexGrow: 1,
                mb: 2,
                p: 2,
                overflowY: 'auto',
                backgroundColor: 'background.default',
                display: 'flex',
                flexDirection: 'column'
              }}
            >
              {activeConversation?.messages.map((msg) => (
                <Box
                  key={msg.id}
                  sx={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    mb: 2,
                  }}
                >
                  <Paper
                    elevation={1}
                    sx={{
                      p: 2,
                      maxWidth: '70%',
                      backgroundColor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                      color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                      borderRadius: 2,
                    }}
                  >
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </Typography>
                  </Paper>
                </Box>
              ))}
              {loading && (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'flex-start',
                    mb: 2,
                  }}
                >
                  <Paper
                    elevation={1}
                    sx={{
                      p: 2,
                      maxWidth: '70%',
                      backgroundColor: 'background.paper',
                      borderRadius: 2,
                    }}
                  >
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {processingLongRequest ? (
                        <>
                          <Typography variant="body1">Still working on your request...</Typography>
                          <Typography variant="caption" color="text.secondary">
                            This is taking longer than expected. The backend server is processing your complex request.
                            {processingTimeDisplay && (
                              <> Processing for {processingTimeDisplay}.</>
                            )}
                          </Typography>
                        </>
                      ) : (
                        <>
                          <Typography variant="body1">Processing your request...</Typography>
                          <Typography variant="caption" color="text.secondary">
                            This may take a minute or two for complex requests. The backend is working on your response.
                          </Typography>
                        </>
                      )}
                    </Box>
                  </Paper>
                </Box>
              )}
            </Paper>

            {/* Message input */}
            <Paper
              component="form"
              onSubmit={handleMessageSubmit}
              sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                borderTop: 1,
                borderColor: 'divider'
              }}
            >
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Type your message..."
                value={message}
                onChange={handleMessageChange}
                disabled={loading}
                sx={{ mr: 2 }}
              />
              <Button
                type="submit"
                variant="contained"
                endIcon={<Send />}
                disabled={!message.trim() || loading}
              >
                Send
              </Button>
            </Paper>
          </Box>

          {/* Tools and components section */}
          <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, width: '100%' }}>
              {/* Terminal/Code Editor */}
              <Box sx={{ width: '100%', flexBasis: { xs: '100%', md: '32%' }, flexGrow: 1 }}>
                <Box sx={{ mb: 1 }}>
                  <Button
                    fullWidth
                    variant="text"
                    startIcon={expandedSections.includes('terminal') ? <ExpandLess /> : <ExpandMore />}
                    onClick={() => toggleSectionExpand('terminal')}
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Terminal/Code Editor
                  </Button>
                </Box>
                <Collapse in={expandedSections.includes('terminal')} timeout="auto" unmountOnExit>
                  <Box sx={{ height: 300 }}>
                    <TerminalEditor conversationId={activeConversation?.id || ''} />
                  </Box>
                </Collapse>
              </Box>

              {/* Web Browsing History */}
              <Box sx={{ width: '100%', flexBasis: { xs: '100%', md: '32%' }, flexGrow: 1 }}>
                <Box sx={{ mb: 1 }}>
                  <Button
                    fullWidth
                    variant="text"
                    startIcon={expandedSections.includes('browsing') ? <ExpandLess /> : <ExpandMore />}
                    onClick={() => toggleSectionExpand('browsing')}
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Web Browsing History
                  </Button>
                </Box>
                <Collapse in={expandedSections.includes('browsing')} timeout="auto" unmountOnExit>
                  <Box sx={{ height: 300 }}>
                    <WebBrowsingHistory conversationId={activeConversation?.id || ''} historyItems={[]} />
                  </Box>
                </Collapse>
              </Box>

              {/* Code Snippet Library */}
              <Box sx={{ width: '100%', flexBasis: { xs: '100%', md: '32%' }, flexGrow: 1 }}>
                <Box sx={{ mb: 1 }}>
                  <Button
                    fullWidth
                    variant="text"
                    startIcon={expandedSections.includes('snippets') ? <ExpandLess /> : <ExpandMore />}
                    onClick={() => toggleSectionExpand('snippets')}
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Code Snippet Library
                  </Button>
                </Box>
                <Collapse in={expandedSections.includes('snippets')} timeout="auto" unmountOnExit>
                  <Box sx={{ height: 300 }}>
                    <CodeSnippetLibrary conversationId={activeConversation?.id || ''} snippets={[]} />
                  </Box>
                </Collapse>
              </Box>

              {/* Thinking Process */}
              <Box sx={{ width: '100%', flexBasis: { xs: '100%', md: '48%' }, flexGrow: 1 }}>
                <Box sx={{ mb: 1 }}>
                  <Button
                    fullWidth
                    variant="text"
                    startIcon={expandedSections.includes('thinking') ? <ExpandLess /> : <ExpandMore />}
                    onClick={() => toggleSectionExpand('thinking')}
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Thinking Process
                  </Button>
                </Box>
                <Collapse in={expandedSections.includes('thinking')} timeout="auto" unmountOnExit>
                  <Box sx={{ height: 300 }}>
                    <ThinkingProcess steps={thinkingSteps} />
                  </Box>
                </Collapse>
              </Box>

              {/* Timeline */}
              <Box sx={{ width: '100%', flexBasis: { xs: '100%', md: '48%' }, flexGrow: 1 }}>
                <Box sx={{ mb: 1 }}>
                  <Button
                    fullWidth
                    variant="text"
                    startIcon={expandedSections.includes('timeline') ? <ExpandLess /> : <ExpandMore />}
                    onClick={() => toggleSectionExpand('timeline')}
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Timeline
                  </Button>
                </Box>
                <Collapse in={expandedSections.includes('timeline')} timeout="auto" unmountOnExit>
                  <Box sx={{ height: 300 }}>
                    <Timeline
                      timelineData={timelineData}
                      conversationId={activeConversation?.id || ''}
                    />
                  </Box>
                </Collapse>
              </Box>
            </Box>
          </Box>
        </Box>
      </Box>

      {/* User Menu */}
      <Menu
        anchorEl={userMenuAnchorEl}
        open={Boolean(userMenuAnchorEl)}
        onClose={handleUserMenuClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <Person fontSize="small" />
          </ListItemIcon>
          <ListItemText>Profile</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <Settings fontSize="small" />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <DarkMode fontSize="small" />
          </ListItemIcon>
          <ListItemText>Dark Mode</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
          <ListItemText>Logout</ListItemText>
        </MenuItem>
      </Menu>
    </ThemeProvider>
  );
};

export default MainLayout;
