/**
 * Tests for the ApiClient class in @/lib/api
 *
 * Covers:
 * - login (sets token in memory + localStorage)
 * - authenticated requests include Authorization header
 * - logout clears token
 * - 401 response clears token and redirects
 * - network / non-OK error handling
 */

import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockFetch = jest.fn();
global.fetch = mockFetch;

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] ?? null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Prevent jsdom from actually navigating
const locationAssign = jest.fn();
const originalLocation = window.location;
beforeAll(() => {
  Object.defineProperty(window, "location", {
    writable: true,
    value: { ...originalLocation, href: "", assign: locationAssign },
  });
});

// ---------------------------------------------------------------------------
// Reset state between tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockFetch.mockReset();
  localStorageMock.clear();
  // Reset internal token by explicitly logging out
  api.logout();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ApiClient", () => {
  // -------------------------------------------------------------------------
  // login
  // -------------------------------------------------------------------------
  describe("login", () => {
    it("sends credentials and stores the returned token", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "tok_abc123" }),
      });

      const result = await api.login("admin", "secret");

      // Verify fetch was called with correct URL and body
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toContain("/api/auth/login");
      expect(opts.method).toBe("POST");
      expect(JSON.parse(opts.body)).toEqual({
        username: "admin",
        password: "secret",
      });

      // Token is returned
      expect(result).toEqual({ access_token: "tok_abc123" });

      // Token persisted to localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "santonibot_token",
        "tok_abc123"
      );

      // Subsequent getToken() returns the token
      expect(api.getToken()).toBe("tok_abc123");
    });
  });

  // -------------------------------------------------------------------------
  // Authenticated requests
  // -------------------------------------------------------------------------
  describe("authenticated requests", () => {
    it("includes Authorization header when a token is present", async () => {
      // Set a token first
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "tok_xyz" }),
      });
      await api.login("user", "pass");

      // Now make an authenticated call (getMe)
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          id: 1,
          username: "user",
          full_name: "User",
          role: "usuario",
          department: "ventas",
        }),
      });
      await api.getMe();

      const [, opts] = mockFetch.mock.calls[1]; // second call
      expect(opts.headers["Authorization"]).toBe("Bearer tok_xyz");
    });

    it("does NOT include Authorization header when no token is set", async () => {
      // No login, token should be null
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ([]),
      });

      await api.getConversations();

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers["Authorization"]).toBeUndefined();
    });
  });

  // -------------------------------------------------------------------------
  // logout
  // -------------------------------------------------------------------------
  describe("logout", () => {
    it("clears the in-memory token and removes it from localStorage", async () => {
      // Set a token
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "tok_to_clear" }),
      });
      await api.login("u", "p");
      expect(api.getToken()).toBe("tok_to_clear");

      api.logout();

      expect(api.getToken()).toBeNull();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        "santonibot_token"
      );
    });
  });

  // -------------------------------------------------------------------------
  // Error handling
  // -------------------------------------------------------------------------
  describe("error handling", () => {
    it("clears token and redirects on 401 response", async () => {
      // Set a token
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "tok_expire" }),
      });
      await api.login("u", "p");

      // Next request returns 401
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Token expired" }),
      });

      await expect(api.getMe()).rejects.toThrow("No autorizado");

      // Token cleared
      expect(api.getToken()).toBeNull();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(
        "santonibot_token"
      );

      // Redirect to login
      expect(window.location.href).toBe("/login");
    });

    it("throws an error with detail message on non-OK response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: "Datos inválidos" }),
      });

      await expect(api.login("u", "p")).rejects.toThrow("Datos inválidos");
    });

    it("throws a generic error when server returns non-JSON body", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("not json");
        },
      });

      await expect(api.getConversations()).rejects.toThrow("Error 500");
    });

    it("propagates network errors from fetch", async () => {
      mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

      await expect(api.getConversations()).rejects.toThrow("Failed to fetch");
    });
  });

  // -------------------------------------------------------------------------
  // sendMessage
  // -------------------------------------------------------------------------
  describe("sendMessage", () => {
    it("sends message payload with optional conversationId", async () => {
      // Login first
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "tok" }),
      });
      await api.login("u", "p");

      // Send message
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          message: "Respuesta",
          conversation_id: 42,
          agent_used: "ventas",
          metadata: null,
        }),
      });

      const result = await api.sendMessage("Hola", 42);

      const [url, opts] = mockFetch.mock.calls[1];
      expect(url).toContain("/api/chat/");
      expect(opts.method).toBe("POST");
      expect(JSON.parse(opts.body)).toEqual({
        message: "Hola",
        conversation_id: 42,
      });
      expect(result.agent_used).toBe("ventas");
    });
  });
});
