import axios from 'axios';
import { Conversation, Message } from '../types';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 120 seconds timeout (increased from 30 seconds)
});

// Add request interceptor for logging
api.interceptors.request.use(config => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error);
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Request error:', error.message);
    }
    return Promise.reject(error);
  }
);

// Mock data for testing when backend is not available
let MOCK_MODE = false; // Default to real API mode, will switch to mock if backend is unavailable

// Function to check if backend is available
// Track the last time we logged a health check to reduce log spam
let lastHealthCheckLogTime = 0;

export const checkBackendAvailability = async (): Promise<boolean> => {
  try {
    const now = Date.now();
    const shouldLog = now - lastHealthCheckLogTime > 60000; // Only log once per minute

    if (shouldLog) {
      console.log('Checking backend availability...');
      lastHealthCheckLogTime = now;
    }

    // Use a longer timeout to give the server more time to respond
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for better reliability

    // Use the same host as the WebSocket connection
    const apiUrl = 'http://localhost:8000/api/health';

    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        },
        mode: 'cors',
        credentials: 'omit',
        signal: controller.signal
      });

      // Clear the timeout since we got a response
      clearTimeout(timeoutId);
    } catch (fetchError) {
      // Clear the timeout
      clearTimeout(timeoutId);
      console.warn('Error fetching health endpoint:', fetchError);
      return false;
    }

    // Handle 429 Too Many Requests specially
    if (response.status === 429) {
      // Get retry-after header or use default backoff
      const retryAfter = response.headers.get('retry-after') ||
                         (await response.json()).retry_after ||
                         5; // Default 5 seconds

      if (shouldLog) {
        console.warn(`Rate limited. Will retry after ${retryAfter} seconds.`);
      }

      // Still return true since the server is available, just rate limiting
      return true;
    }

    if (response.ok) {
      // Parse the response to get more details
      const data = await response.json();

      if (shouldLog) {
        console.log('Backend health check response:', data);
        console.log('Backend is available!');
      }

      // If we get a successful response, ensure MOCK_MODE is false
      MOCK_MODE = false;

      return true;
    } else {
      console.warn(`Backend returned status ${response.status}: ${response.statusText}`);
      return false;
    }
  } catch (error) {
    const err = error as Error;
    console.warn('Backend server appears to be unavailable:', err.name, err.message || 'Unknown error');

    // Log more details about the error
    if (err.name === 'AbortError') {
      console.warn('Request was aborted due to timeout');
    } else if (err.name === 'TypeError' && err.message.includes('Failed to fetch')) {
      console.warn('Network error: server might be down or unreachable');
    }

    return false;
  }
};

// Track the last time we logged a mode change to reduce log spam
let lastModeChangeLogTime = 0;
let lastModeState: boolean | null = null;

// Check backend availability and set MOCK_MODE accordingly
const checkAndSetMockMode = async () => {
  const isAvailable = await checkBackendAvailability();
  const now = Date.now();
  const modeChanged = lastModeState !== isAvailable;
  const shouldLog = modeChanged || (now - lastModeChangeLogTime > 60000); // Log on change or once per minute

  if (!isAvailable) {
    if (shouldLog) {
      console.warn('Backend server is not available. Switching to mock mode.');
      lastModeChangeLogTime = now;
    }
    MOCK_MODE = true;
  } else {
    if (shouldLog) {
      console.log('Backend server is available. Using real API.');
      lastModeChangeLogTime = now;
    }
    MOCK_MODE = false; // Explicitly set to false to ensure we use the real API
  }

  lastModeState = isAvailable;
};

// Initial check
checkAndSetMockMode();

// Periodically check backend availability
setInterval(checkAndSetMockMode, 60000); // Check every 60 seconds (reduced from 10 seconds to reduce server load)

// Generate a mock response for testing
const generateMockResponse = (content: string): Message => {
  return {
    id: `mock-${Date.now()}`,
    role: 'assistant',
    content: `This is a mock response to: "${content}". The backend API is not available.`,
    timestamp: Date.now(),
  };
};

// API functions
export const sendMessage = async (
  content: string,
  conversationId?: string,
  systemPrompt?: string,
  parameters?: Record<string, any>
): Promise<Message> => {
  try {
    // If in mock mode, return mock data
    if (MOCK_MODE) {
      console.log('Using mock data for sendMessage');
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      return generateMockResponse(content);
    }

    // Check backend availability before making the call
    const isBackendAvailable = await checkBackendAvailability();
    if (!isBackendAvailable) {
      console.warn('Backend is not available, switching to mock mode for this request');
      MOCK_MODE = true;
      return generateMockResponse(content);
    }

    console.log('Sending message to backend:', content);
    // Real API call
    const response = await api.post('/api/message', {
      content,
      conversation_id: conversationId,
      system_prompt: systemPrompt,
      parameters,
    });

    console.log('Received response from backend:', response.data);
    // If we get a successful response, ensure mock mode is off
    MOCK_MODE = false;
    return response.data;
  } catch (error) {
    console.error('Error sending message:', error);

    // Analyze the error to determine if it's a timeout or a connection issue
    const err = error as { message?: string, code?: string, isAxiosError?: boolean };

    // Check if it's a timeout error
    if (err.message && err.message.includes('timeout')) {
      console.warn('Request timed out. The backend is likely still processing your request.');

      // Return a more informative message about timeouts
      return {
        id: `processing-${Date.now()}`,
        role: 'assistant',
        content: 'Your request is taking longer than expected to process. The backend server is working on it, ' +
                 'but it might take a few minutes. Please wait and try again later if you don\'t receive a response.',
        timestamp: Date.now(),
      };
    }
    // Check if it's a connection error
    else if (err.message && (err.message.includes('Network Error') || err.message.includes('ECONNREFUSED'))) {
      console.warn('Network error detected. Switching to mock mode for future requests.');
      MOCK_MODE = true;

      // Return a helpful error message about connection issues
      return {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, there was an error connecting to the backend server. The server appears to be unavailable. ' +
                 'Please check if the server is running at http://localhost:8000 or contact your administrator.',
        timestamp: Date.now(),
      };
    }
    // For other types of errors
    else {
      console.warn('Unknown error occurred during message processing.');

      // Return a generic error message
      return {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again or contact your administrator if the issue persists.',
        timestamp: Date.now(),
      };
    }
  }
};

// Mock conversations for testing
const mockConversations: Conversation[] = [
  {
    id: 'mock-1',
    title: 'Mock Conversation 1',
    messages: [
      {
        id: 'mock-msg-1',
        role: 'user',
        content: 'Hello',
        timestamp: Date.now() - 60000,
      },
      {
        id: 'mock-msg-2',
        role: 'assistant',
        content: 'Hi there! How can I help you today?',
        timestamp: Date.now() - 55000,
      },
    ],
    created_at: Date.now() - 60000,
    updated_at: Date.now() - 55000,
  },
  {
    id: 'mock-2',
    title: 'Mock Conversation 2',
    messages: [],
    created_at: Date.now() - 120000,
    updated_at: Date.now() - 120000,
  },
];

// Mock timeline data
const mockTimelineData = {
  events: [
    {
      id: 'event-1',
      type: 'user_input',
      name: 'User Message',
      description: 'User sent a message',
      start_time: Date.now() - 60000,
      end_time: Date.now() - 59000,
      metadata: {},
    },
    {
      id: 'event-2',
      type: 'thinking',
      name: 'Processing Request',
      description: 'Analyzing user input',
      start_time: Date.now() - 59000,
      end_time: Date.now() - 57000,
      metadata: {
        confidence: 0.85,
      },
      children: [
        {
          id: 'event-2-1',
          type: 'thinking',
          name: 'Natural Language Understanding',
          description: 'Parsing user intent',
          start_time: Date.now() - 59000,
          end_time: Date.now() - 58500,
          metadata: {},
        },
        {
          id: 'event-2-2',
          type: 'thinking',
          name: 'Response Generation',
          description: 'Creating appropriate response',
          start_time: Date.now() - 58500,
          end_time: Date.now() - 57000,
          metadata: {},
        },
      ],
    },
    {
      id: 'event-3',
      type: 'response',
      name: 'Assistant Response',
      description: 'Generated response to user',
      start_time: Date.now() - 57000,
      end_time: Date.now() - 55000,
      metadata: {},
    },
  ],
  event_count: 3,
};

export const getConversations = async (): Promise<Conversation[]> => {
  try {
    if (MOCK_MODE) {
      console.log('Using mock data for getConversations');
      await new Promise(resolve => setTimeout(resolve, 500));
      return mockConversations;
    }

    // Check backend availability before making the call
    const isBackendAvailable = await checkBackendAvailability();
    if (!isBackendAvailable) {
      console.warn('Backend is not available, switching to mock mode for this request');
      MOCK_MODE = true;
      return mockConversations;
    }

    console.log('Fetching conversations from backend');
    const response = await api.get('/api/conversations');
    console.log('Received conversations from backend:', response.data);

    // If we get a successful response, ensure mock mode is off
    MOCK_MODE = false;

    // If the response is empty, return mock conversations
    if (!response.data || response.data.length === 0) {
      console.log('No conversations found, using mock data');
      return mockConversations;
    }

    return response.data;
  } catch (error) {
    console.error('Error getting conversations:', error);

    // Set MOCK_MODE to true for future requests if we get a connection error
    const err = error as { message?: string };
    if (err.message && (err.message.includes('Network Error') ||
                        err.message.includes('timeout') ||
                        err.message.includes('ECONNREFUSED'))) {
      console.warn('Network error detected. Switching to mock mode for future requests.');
      MOCK_MODE = true;
    }

    return mockConversations;
  }
};

export const getConversation = async (conversationId: string): Promise<Conversation> => {
  try {
    if (MOCK_MODE) {
      console.log('Using mock data for getConversation');
      await new Promise(resolve => setTimeout(resolve, 500));
      const conversation = mockConversations.find(c => c.id === conversationId);
      if (conversation) {
        return conversation;
      }
      return mockConversations[0];
    }

    const response = await api.get(`/api/conversations/${conversationId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting conversation:', error);
    return mockConversations[0];
  }
};

export const getConversationTimeline = async (conversationId: string): Promise<any> => {
  try {
    if (MOCK_MODE) {
      console.log('Using mock data for getConversationTimeline');
      await new Promise(resolve => setTimeout(resolve, 500));
      return mockTimelineData;
    }

    const response = await api.get(`/api/conversations/${conversationId}/timeline`);
    return response.data;
  } catch (error) {
    console.error('Error getting conversation timeline:', error);
    return mockTimelineData;
  }
};

// WebSocket connection for timeline updates
export const createTimelineWebSocket = async (
  conversationId: string,
  onMessage: (data: any) => void
): Promise<WebSocket> => {
  if (MOCK_MODE) {
    console.log('Using mock WebSocket for timeline updates');
    // Create a mock WebSocket that simulates periodic updates
    const mockWs = {
      close: () => console.log('Mock WebSocket closed'),
      send: (data: string) => console.log('Mock WebSocket send:', data),
      onopen: null as any,
      onmessage: null as any,
      onerror: null as any,
      onclose: null as any,
      readyState: 1, // OPEN
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
      url: `ws://localhost:8000/api/ws/timeline/${conversationId}`,
      protocol: '',
      extensions: '',
      bufferedAmount: 0,
      binaryType: 'blob' as BinaryType,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => true,
    };

    // Simulate connection open
    setTimeout(() => {
      if (mockWs.onopen) mockWs.onopen({} as Event);
    }, 100);

    // Simulate periodic updates
    const interval = setInterval(() => {
      if (mockWs.onmessage) {
        const mockEvent = {
          data: JSON.stringify({
            type: 'timeline_update',
            timeline: {
              ...mockTimelineData,
              events: [
                ...mockTimelineData.events,
                {
                  id: `event-${Date.now()}`,
                  type: 'thinking',
                  name: 'New Thinking Process',
                  description: 'Processing new information',
                  start_time: Date.now() - 5000,
                  end_time: Date.now(),
                  metadata: {
                    confidence: Math.random() * 0.5 + 0.5, // Random confidence between 0.5 and 1.0
                  },
                },
              ],
            },
          }),
        };
        mockWs.onmessage(mockEvent as MessageEvent);
      }
    }, 10000); // Send update every 10 seconds

    // Clean up interval when WebSocket is closed
    const originalClose = mockWs.close;
    mockWs.close = () => {
      clearInterval(interval);
      console.log('Mock WebSocket closed');
      if (mockWs.onclose) mockWs.onclose({} as CloseEvent);
      return originalClose.call(mockWs);
    };

    return mockWs as unknown as WebSocket;
  }

  // Real WebSocket connection
  try {
    // Check if backend is available before creating WebSocket
    const isAvailable = await checkBackendAvailability();

    if (!isAvailable) {
      console.warn('Backend is not available, using mock WebSocket');
      MOCK_MODE = true;
      return await createTimelineWebSocket(conversationId, onMessage);
    }

    // If we're in mock mode but backend is available, switch to real mode
    if (MOCK_MODE) {
      console.log('Backend is available, switching to real WebSocket');
      MOCK_MODE = false;
    }

    // Create WebSocket with a more reliable connection approach
    console.log(`Creating WebSocket connection for conversation ${conversationId}`);

    // Use a more robust WebSocket URL construction
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = 'localhost:8000'; // In production, this should match your backend host
    const wsUrl = `${wsProtocol}//${wsHost}/api/ws/timeline/${conversationId}`;

    console.log(`WebSocket URL: ${wsUrl}`);

    // Force a health check before creating the WebSocket
    const healthCheck = await checkBackendAvailability();
    if (!healthCheck) {
      console.warn('Health check failed before creating WebSocket, using mock mode');
      MOCK_MODE = true;
      return await createTimelineWebSocket(conversationId, onMessage);
    }

    // Create the WebSocket with error handling
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      MOCK_MODE = true;
      return await createTimelineWebSocket(conversationId, onMessage);
    }

    // Set a connection timeout
    const connectionTimeout = setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket connection timeout - closing socket');
        try {
          ws.close();
        } catch (e) {
          console.warn('Error closing WebSocket after timeout:', e);
        }
      }
    }, 15000); // 15 second timeout for better stability

    ws.onopen = () => {
      console.log(`WebSocket connection established for conversation ${conversationId}`);
      // Clear the connection timeout
      clearTimeout(connectionTimeout);
      // If connection is successful, ensure MOCK_MODE is false
      MOCK_MODE = false;

      // Send a ping immediately to verify the connection
      try {
        ws.send(JSON.stringify({ type: 'ping' }));
      } catch (error) {
        console.error('Error sending initial ping:', error);
      }
    };

    ws.onmessage = (event) => {
      try {
        // Log the raw message for debugging
        console.debug(`WebSocket message received for ${conversationId}:`,
          typeof event.data === 'string' ? event.data.substring(0, 100) + '...' : 'Non-string data');

        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data.type || 'unknown type');

        // Update lastPongTime when we receive a pong or any message from the server
        lastPongTime = Date.now();

        // Only pass timeline updates to the callback
        if (data.type === 'timeline_update') {
          console.log(`Timeline update received for ${conversationId}`);
          onMessage(data);
        } else if (data.type === 'ping') {
          // Respond to ping with a pong
          console.debug(`Ping received from server for ${conversationId}, sending pong`);
          try {
            ws.send(JSON.stringify({ type: "pong", timestamp: Date.now() }));
          } catch (e) {
            console.warn(`Error sending pong response for ${conversationId}:`, e);
          }
        } else if (data.type === 'pong') {
          console.log('Received pong from server');
        } else if (data.type === 'connection_established') {
          console.log('Connection established with server');
        } else {
          console.log(`Unknown message type received for ${conversationId}:`, data.type);
        }
      } catch (error) {
        console.error(`Error parsing WebSocket message for ${conversationId}:`, error);
        console.error('Raw message:',
          typeof event.data === 'string' ? event.data.substring(0, 200) + '...' : 'Non-string data');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Log the error but don't switch to mock mode immediately
      // The connection might still recover or the close handler will handle it
      console.log('WebSocket encountered an error, will attempt to reconnect if disconnected');
    };

    // Set up a heartbeat to keep the connection alive
    let heartbeatInterval: number | null = null;
    let lastPongTime = Date.now();

    const startHeartbeat = () => {
      if (heartbeatInterval) clearInterval(heartbeatInterval);

      heartbeatInterval = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            // Check if we've received a pong recently
            const now = Date.now();
            const timeSinceLastPong = now - lastPongTime;

            // If it's been more than 2 minutes since last pong, consider the connection dead
            if (timeSinceLastPong > 120000) { // 2 minutes
              console.warn('No pong received for 2 minutes, closing connection');
              ws.close();
              return;
            }

            // Send ping less frequently (every 45 seconds instead of 30)
            ws.send(JSON.stringify({ type: 'ping', timestamp: now }));
            console.log('Sent heartbeat ping');
          } catch (error) {
            console.error('Error sending heartbeat ping:', error);
            // If we can't send a ping, the connection might be dead
            if (ws.readyState === WebSocket.OPEN) {
              ws.close();
            }
          }
        } else if (ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
          if (heartbeatInterval) clearInterval(heartbeatInterval);
        }
      }, 45000); // Send a ping every 45 seconds (increased from 30 seconds)
    };

    // Start the heartbeat when the connection opens
    ws.addEventListener('open', startHeartbeat);

    ws.onclose = async (event) => {
      console.log(`WebSocket connection closed for conversation ${conversationId}:`, event.code, event.reason);

      // Clear the heartbeat interval
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
      }

      // For normal closure codes, just log and don't reconnect
      if (event.code === 1000 || event.code === 1001) {
        console.log('WebSocket closed normally');
        return;
      }

      // For specific error codes that indicate a permanent issue with this conversation
      if (event.code === 1003 || event.code === 1008) {
        console.warn(`WebSocket connection was rejected with code ${event.code}: ${event.reason}`);
        // Don't switch to mock mode globally, just for this specific conversation
        console.log('Using mock WebSocket for this conversation only');
        MOCK_MODE = true;
        return await createTimelineWebSocket(conversationId, onMessage);
      }

      // For all other unexpected closures, try to reconnect after a delay
      console.log('Attempting to reconnect WebSocket in 5 seconds...');

      // Use a promise to handle the reconnection
      return new Promise<WebSocket>((resolve) => {
        setTimeout(async () => {
          try {
            // Check if the backend is available before reconnecting
            const isAvailable = await checkBackendAvailability();

            if (isAvailable) {
              console.log('Backend is available, reconnecting WebSocket...');
              MOCK_MODE = false;
              const newWs = await createTimelineWebSocket(conversationId, onMessage);
              resolve(newWs);
            } else {
              console.log('Backend is still unavailable, using mock WebSocket');
              MOCK_MODE = true;
              const mockWs = await createTimelineWebSocket(conversationId, onMessage);
              resolve(mockWs);
            }
          } catch (error) {
            console.error('Error during WebSocket reconnection:', error);
            MOCK_MODE = true;
            const fallbackWs = await createTimelineWebSocket(conversationId, onMessage);
            resolve(fallbackWs);
          }
        }, 5000); // Increased from 3 to 5 seconds to reduce reconnection frequency
      });
    };

    return ws;
  } catch (error) {
    console.error('Error creating WebSocket:', error);
    // Switch to mock mode if we can't create a real WebSocket
    MOCK_MODE = true;
    // Return a dummy WebSocket object that does nothing
    return {
      close: () => {},
      send: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => true,
      readyState: WebSocket.CLOSED,
    } as unknown as WebSocket;
  }
};
