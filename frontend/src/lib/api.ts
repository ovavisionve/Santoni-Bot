const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

  // Auth
  async login(username: string, password: string, totp_code?: string) {
    const data = await this.request<{
      access_token: string;
      totp_required?: boolean;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password, totp_code: totp_code || null }),
    });
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

  // Chat
  async sendMessage(message: string, conversationId?: number) {
    return this.request<import("@/types").ChatResponse>("/api/chat/", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId || null,
      }),
    });
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
  }) {
    return this.request<import("@/types").User>("/api/users/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateUser(
    id: number,
    data: Partial<import("@/types").User & { password?: string }>
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
}

export const api = new ApiClient();
