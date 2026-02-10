/**
 * Tests for the useAuth hook.
 *
 * Covers:
 * - login flow (calls api.login, api.getMe, sets user)
 * - logout flow (clears user)
 * - checkAuth with a valid token (restores user)
 * - checkAuth with no token (stays unauthenticated)
 * - checkAuth when getMe fails (clears token)
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import type { User } from "@/types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock("@/lib/api", () => ({
  api: {
    getToken: jest.fn(),
    login: jest.fn(),
    getMe: jest.fn(),
    logout: jest.fn(),
  },
}));

const mockApi = api as jest.Mocked<typeof api>;

const fakeUser: User = {
  id: 1,
  email: "carlos@santoni.com",
  username: "carlos",
  full_name: "Carlos Perez",
  role: "usuario",
  department: "ventas",
  extra_departments: null,
  is_active: true,
  created_at: "2025-01-01T00:00:00Z",
};

// ---------------------------------------------------------------------------
// Reset mocks
// ---------------------------------------------------------------------------

beforeEach(() => {
  jest.clearAllMocks();
  // By default, no stored token
  mockApi.getToken.mockReturnValue(null);
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useAuth", () => {
  // -----------------------------------------------------------------------
  // checkAuth (runs on mount)
  // -----------------------------------------------------------------------
  describe("checkAuth on mount", () => {
    it("sets loading=false immediately when there is no token", async () => {
      mockApi.getToken.mockReturnValue(null);

      const { result } = renderHook(() => useAuth());

      // Initially loading may be true, then turns false once effect runs
      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.user).toBeNull();
      expect(mockApi.getMe).not.toHaveBeenCalled();
    });

    it("restores user when a valid token exists", async () => {
      mockApi.getToken.mockReturnValue("valid-token");
      mockApi.getMe.mockResolvedValue(fakeUser);

      const { result } = renderHook(() => useAuth());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.user).toEqual(fakeUser);
      expect(mockApi.getMe).toHaveBeenCalledTimes(1);
    });

    it("clears token and sets user null when getMe fails", async () => {
      mockApi.getToken.mockReturnValue("expired-token");
      mockApi.getMe.mockRejectedValue(new Error("No autorizado"));

      const { result } = renderHook(() => useAuth());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.user).toBeNull();
      expect(mockApi.logout).toHaveBeenCalledTimes(1);
    });
  });

  // -----------------------------------------------------------------------
  // login
  // -----------------------------------------------------------------------
  describe("login", () => {
    it("calls api.login and api.getMe, then sets the user", async () => {
      mockApi.getToken.mockReturnValue(null);
      mockApi.login.mockResolvedValue({ access_token: "new-token" });
      mockApi.getMe.mockResolvedValue(fakeUser);

      const { result } = renderHook(() => useAuth());

      // Wait for initial loading to finish
      await waitFor(() => expect(result.current.loading).toBe(false));

      let returnedUser: User | undefined;
      await act(async () => {
        returnedUser = await result.current.login("carlos", "pass123");
      });

      expect(mockApi.login).toHaveBeenCalledWith("carlos", "pass123");
      expect(mockApi.getMe).toHaveBeenCalled();
      expect(result.current.user).toEqual(fakeUser);
      expect(returnedUser).toEqual(fakeUser);
    });

    it("propagates login errors to the caller", async () => {
      mockApi.getToken.mockReturnValue(null);
      mockApi.login.mockRejectedValue(new Error("Credenciales inválidas"));

      const { result } = renderHook(() => useAuth());
      await waitFor(() => expect(result.current.loading).toBe(false));

      await expect(
        act(async () => {
          await result.current.login("bad", "creds");
        })
      ).rejects.toThrow("Credenciales inválidas");

      expect(result.current.user).toBeNull();
    });
  });

  // -----------------------------------------------------------------------
  // logout
  // -----------------------------------------------------------------------
  describe("logout", () => {
    it("calls api.logout and sets user to null", async () => {
      // Start with a logged-in user
      mockApi.getToken.mockReturnValue("valid-token");
      mockApi.getMe.mockResolvedValue(fakeUser);

      const { result } = renderHook(() => useAuth());
      await waitFor(() => expect(result.current.user).toEqual(fakeUser));

      act(() => {
        result.current.logout();
      });

      expect(mockApi.logout).toHaveBeenCalled();
      expect(result.current.user).toBeNull();
    });
  });
});
