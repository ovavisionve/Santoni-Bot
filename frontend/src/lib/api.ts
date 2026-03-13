const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("santonibot_token", token);
    } else {
      localStorage.removeItem("santonibot_token");
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("santonibot_token");
    }
    return this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.setToken(null);
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("No autorizado");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Error ${response.status}`);
    }

    return response.json();
  }

  // Auth – handled separately to avoid the generic 401 redirect
  async login(username: string, password: string, totp_code?: string) {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, totp_code: totp_code || null }),
      });
    } catch {
      throw new Error(
        "No se pudo conectar con el servidor. Verifique que el backend esté activo."
      );
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Error del servidor (${response.status})`);
    }

    const data = await response.json();
    if (data.totp_required) {
      return { totp_required: true as const, access_token: "" };
    }
    this.setToken(data.access_token);
    return data;
  }

  // TOTP 2FA
  async totpSetup() {
    return this.request<import("@/types").TOTPSetup>("/api/auth/totp/setup", {
      method: "POST",
    });
  }

  async totpEnable(totp_code: string) {
    return this.request<{ message: string }>("/api/auth/totp/enable", {
      method: "POST",
      body: JSON.stringify({ totp_code }),
    });
  }

  async totpDisable(totp_code: string) {
    return this.request<{ message: string }>("/api/auth/totp/disable", {
      method: "POST",
      body: JSON.stringify({ totp_code }),
    });
  }

  // Password
  async changePassword(current_password: string, new_password: string) {
    return this.request<{ message: string }>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    });
  }

  logout() {
    this.setToken(null);
  }

  async getMe() {
    return this.request<import("@/types").User>("/api/auth/me");
  }

  // Documents
  async uploadDocument(file: File): Promise<{
    file_id: string;
    filename: string;
    size: number;
    extension: string;
    can_analyze_full: boolean;
    message: string;
  }> {
    const token = this.getToken();
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (response.status === 401) {
      this.setToken(null);
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("No autorizado");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Error ${response.status}`);
    }

    return response.json();
  }

  // Chat
  async getAgents() {
    return this.request<{ name: string; display_name: string; department: string; description: string }[]>(
      "/api/chat/agents"
    );
  }

  async sendMessage(message: string, conversationId?: number, fileId?: string, agentName?: string) {
    return this.request<import("@/types").ChatResponse>("/api/chat/", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId || null,
        file_id: fileId || null,
        agent_name: agentName || null,
      }),
    });
  }

  /**
   * Stream a chat response via SSE. Calls onToken for each token,
   * onMeta when metadata arrives, and returns the final done event.
   */
  async streamMessage(
    message: string,
    callbacks: {
      onToken: (token: string) => void;
      onMeta?: (data: { conversation_id: number; agent: string; timestamp?: string }) => void;
      onError?: (error: string) => void;
    },
    conversationId?: number,
    agentName?: string,
  ): Promise<{ message_id: number; conversation_id: number }> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        message,
        conversation_id: conversationId || null,
        file_id: null,
        agent_name: agentName || null,
      }),
    });

    if (response.status === 401) {
      this.setToken(null);
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new Error("No autorizado");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Error ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("Stream not available");

    const decoder = new TextDecoder();
    let result = { message_id: 0, conversation_id: conversationId || 0 };
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "token") {
            callbacks.onToken(data.content);
          } else if (data.type === "meta") {
            result.conversation_id = data.conversation_id;
            callbacks.onMeta?.(data);
          } else if (data.type === "error") {
            callbacks.onError?.(data.content);
          } else if (data.type === "done") {
            result = { message_id: data.message_id, conversation_id: data.conversation_id };
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }

    return result;
  }

  async getConversations() {
    return this.request<import("@/types").ConversationListItem[]>(
      "/api/chat/conversations"
    );
  }

  async getConversation(id: number) {
    return this.request<import("@/types").Conversation>(
      `/api/chat/conversations/${id}`
    );
  }

  async deleteConversation(id: number) {
    return this.request(`/api/chat/conversations/${id}`, {
      method: "DELETE",
    });
  }

  async updateConversationTitle(id: number, title: string) {
    return this.request<import("@/types").Conversation>(
      `/api/chat/conversations/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }
    );
  }

  // Admin
  async getUsers() {
    return this.request<import("@/types").User[]>("/api/users/");
  }

  async createUser(data: {
    email: string;
    username: string;
    full_name: string;
    password: string;
    role: string;
    department: string;
    extra_departments?: string | null;
    allowed_org_ids?: string | null;
    idempiere_salesrep_id?: number | null;
  }) {
    return this.request<import("@/types").User>("/api/users/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getOrganizations() {
    return this.request<import("@/types").Organization[]>(
      "/api/users/organizations"
    );
  }

  async getSalesreps() {
    return this.request<{ id: number; name: string }[]>(
      "/api/users/salesreps"
    );
  }

  async updateUser(
    id: number,
    data: {
      admin_password: string;
      email?: string;
      full_name?: string;
      role?: string;
      department?: string;
      extra_departments?: string | null;
      allowed_org_ids?: string | null;
      idempiere_salesrep_id?: number | null;
      sensitivity_level?: number;
      is_active?: boolean;
      new_password?: string | null;
    }
  ) {
    return this.request<import("@/types").User>(`/api/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteUser(id: number) {
    return this.request(`/api/users/${id}`, { method: "DELETE" });
  }

  async getStats() {
    return this.request<import("@/types").SystemStats>("/api/admin/stats");
  }

  async getAuditLogs(page = 1, limit = 50) {
    return this.request<{
      total: number;
      page: number;
      data: Array<{
        id: number;
        user_id: number;
        username: string | null;
        full_name: string | null;
        action: string;
        resource: string;
        detail: string;
        agent_used: string;
        ip_address: string | null;
        created_at: string;
      }>;
    }>(`/api/admin/audit-logs?page=${page}&limit=${limit}`);
  }

  // Security management
  async getSecurityOverview() {
    return this.request<{
      failed_logins_24h: number;
      account_lockouts_7d: number;
      currently_locked: number;
      totp_enabled_users: number;
      total_active_users: number;
      totp_coverage_pct: number;
      suspicious_ips: Array<{ ip: string; failed_attempts: number }>;
    }>("/api/admin/security/overview");
  }

  async getLockedUsers() {
    return this.request<
      Array<{
        id: number;
        username: string;
        full_name: string;
        department: string;
        failed_attempts: number;
        locked_until: string | null;
        remaining_minutes: number;
      }>
    >("/api/admin/security/locked-users");
  }

  async unlockUser(userId: number) {
    return this.request<{ message: string }>(
      `/api/admin/security/unlock-user/${userId}`,
      { method: "POST" }
    );
  }

  // Dashboard & KPIs
  async getDashboardKPIs() {
    return this.request<{
      user: { name: string; department: string; departments: string[]; role: string };
      activity: { conversations: number; messages_7d: number };
      kpis: Record<string, unknown>;
      timestamp: string;
    }>("/api/dashboard/kpis");
  }

  async getDashboardAlerts() {
    return this.request<{
      alerts: Array<{
        type: string;
        department: string;
        title: string;
        message: string;
        metric: string;
        value: number;
      }>;
      count: number;
    }>("/api/dashboard/alerts");
  }

  // User conversations (admin audit)
  async getUserConversations(userId: number) {
    return this.request<{
      user: { id: number; username: string; full_name: string; department: string | null };
      conversations: Array<{
        id: number;
        title: string;
        created_at: string | null;
        message_count: number;
        messages: Array<{
          role: string;
          content: string;
          agent_used: string | null;
          created_at: string | null;
        }>;
      }>;
      total: number;
    }>(`/api/admin/users/${userId}/conversations`);
  }

  exportUserConversationsUrl(userId: number, format: "txt" | "pdf" = "txt"): string {
    return `${API_BASE}/api/admin/users/${userId}/conversations/export?format=${format}`;
  }

  // User conversation export (own conversations)
  exportConversationUrl(conversationId: number, format: "txt" | "pdf" = "txt"): string {
    return `${API_BASE}/api/chat/conversations/${conversationId}/export?format=${format}`;
  }

  exportAllConversationsUrl(format: "txt" | "pdf" = "txt"): string {
    return `${API_BASE}/api/chat/conversations/export-all?format=${format}`;
  }

  /**
   * Download a file from a URL that requires auth token.
   * Fetches the blob and triggers a download programmatically.
   */
  async downloadFile(url: string, fallbackFilename: string): Promise<void> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Error ${response.status}`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition");
    let filename = fallbackFilename;
    if (disposition) {
      const match = disposition.match(/filename="?([^";\n]+)"?/);
      if (match) filename = match[1];
    }

    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  // Usage metrics (admin/supervisor)
  async getUsageMetrics(days = 7) {
    return this.request<{
      period_days: number;
      daily_messages: Array<{ date: string; count: number }>;
      daily_conversations: Array<{ date: string; count: number }>;
      top_users: Array<{ username: string; full_name: string; department: string; message_count: number }>;
      department_breakdown: Array<{ department: string; active_users: number; messages: number }>;
      avg_messages_per_conversation: number;
    }>(`/api/admin/metrics?days=${days}`);
  }
}

export const api = new ApiClient();
