export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: "usuario" | "supervisor" | "administrador";
  department: string;
  extra_departments: string | null;
  is_active: boolean;
  avatar_url: string | null;
  totp_enabled: boolean;
  created_at: string;
}

export interface Branding {
  company_name: string;
  company_subtitle: string;
  primary_color: string;
  logo_url: string;
  login_logo_url: string;
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
  totp_required?: boolean;
}

export interface TOTPSetup {
  secret: string;
  qr_uri: string;
}

export interface SystemStats {
  users: { total: number; active: number };
  conversations: number;
  messages: number;
  agent_usage: Record<string, number>;
}
