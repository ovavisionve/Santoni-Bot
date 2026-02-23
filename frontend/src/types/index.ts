export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: "usuario" | "supervisor" | "administrador" | "vendedor";
  department: string;
  extra_departments: string | null;
  allowed_org_ids: string | null;
  idempiere_salesrep_id: number | null;
  is_active: boolean;
  totp_enabled: boolean;
  created_at: string;
}

export interface Organization {
  id: number;
  value: string;
  name: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  agent_used: string | null;
  created_at: string;
  data_timestamp?: string | null;
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
