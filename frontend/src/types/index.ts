// Common types for the application

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  timeline?: TimelineData;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: number;
  updated_at: number;
}

export interface TimelineEvent {
  id: string;
  type: string;
  name: string;
  description?: string;
  start_time: number;
  end_time?: number;
  parent_id?: string;
  metadata?: Record<string, any>;
  children?: TimelineEvent[];
}

export interface TimelineData {
  events: TimelineEvent[];
  event_count: number;
}

export interface WebBrowsingHistoryItem {
  id: string;
  url: string;
  title: string;
  timestamp: number;
  preview?: string;
  conversation_id: string;
}

export interface CodeSnippet {
  id: string;
  title: string;
  language: string;
  code: string;
  tags: string[];
  created_at: number;
  updated_at: number;
  conversation_id?: string;
}

export interface TerminalCommand {
  id: string;
  command: string;
  output: string;
  timestamp: number;
  conversation_id: string;
}

export interface ThinkingProcessStep {
  id: string;
  step: number;
  description: string;
  reasoning: string;
  confidence: number;
  alternatives?: string[];
  references?: string[];
  timestamp: number;
  isFinalOutput?: boolean;
}

export interface ApiError {
  status: number;
  message: string;
  details?: any;
}
