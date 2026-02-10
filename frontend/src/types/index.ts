export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: "usuario" | "supervisor" | "administrador";
  department: string;
  extra_departments: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  agent_used: string | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface ConversationListItem {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview?: string;
}

export interface ChatResponse {
  message: string;
  message_id: number;
  conversation_id: number;
  agent_used: string | null;
  metadata: Record<string, unknown> | null;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}

export interface SystemStats {
  users: { total: number; active: number };
  conversations: number;
  messages: number;
  agent_usage: Record<string, number>;
}
