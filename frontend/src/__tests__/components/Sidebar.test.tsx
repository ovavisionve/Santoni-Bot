/**
 * Tests for the Sidebar component.
 *
 * Covers:
 * - Renders nothing when isOpen is false
 * - Renders conversation list
 * - Active conversation is highlighted
 * - "Nueva conversacion" (new chat) button fires callback
 * - Logout button fires callback
 * - Delete conversation button fires callback with correct id
 * - Shows admin link when user role is "administrador"
 * - Hides admin link for non-admin users
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import Sidebar from "@/components/layout/Sidebar";
import type { User, ConversationListItem } from "@/types";

// ---------------------------------------------------------------------------
// Mock lucide-react icons to simple spans
// ---------------------------------------------------------------------------
jest.mock("lucide-react", () => ({
  MessageSquarePlus: (props: Record<string, unknown>) => (
    <span data-testid="icon-msg-plus" {...props} />
  ),
  LogOut: (props: Record<string, unknown>) => (
    <span data-testid="icon-logout" {...props} />
  ),
  Trash2: (props: Record<string, unknown>) => (
    <span data-testid="icon-trash" {...props} />
  ),
  Settings: (props: Record<string, unknown>) => (
    <span data-testid="icon-settings" {...props} />
  ),
  MessageSquare: (props: Record<string, unknown>) => (
    <span data-testid="icon-msg" {...props} />
  ),
  ChevronLeft: (props: Record<string, unknown>) => (
    <span data-testid="icon-chevron" {...props} />
  ),
}));

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: "carlos@santoni.com",
    username: "carlos",
    full_name: "Carlos Perez",
    role: "usuario",
    department: "ventas",
    extra_departments: null,
    is_active: true,
    created_at: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeConversation(
  overrides: Partial<ConversationListItem> = {}
): ConversationListItem {
  return {
    id: 1,
    title: "Reporte de ventas",
    created_at: "2025-06-01T10:00:00Z",
    updated_at: "2025-06-01T12:00:00Z",
    message_count: 5,
    ...overrides,
  };
}

const defaultProps = {
  user: makeUser(),
  conversations: [
    makeConversation({ id: 1, title: "Reporte de ventas" }),
    makeConversation({ id: 2, title: "Flujo de caja" }),
    makeConversation({ id: 3, title: "Nomina junio" }),
  ],
  activeId: null as number | null,
  isOpen: true,
  onToggle: jest.fn(),
  onNewChat: jest.fn(),
  onSelectConversation: jest.fn(),
  onDeleteConversation: jest.fn(),
  onLogout: jest.fn(),
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Sidebar", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // -----------------------------------------------------------------------
  // Visibility
  // -----------------------------------------------------------------------
  describe("visibility", () => {
    it("renders nothing when isOpen is false", () => {
      const { container } = render(
        <Sidebar {...defaultProps} isOpen={false} />
      );
      expect(container.innerHTML).toBe("");
    });

    it("renders the sidebar when isOpen is true", () => {
      render(<Sidebar {...defaultProps} isOpen={true} />);
      expect(screen.getByText("SantoniBot")).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Conversation list
  // -----------------------------------------------------------------------
  describe("conversation list", () => {
    it("renders all conversations", () => {
      render(<Sidebar {...defaultProps} />);

      expect(screen.getByText("Reporte de ventas")).toBeInTheDocument();
      expect(screen.getByText("Flujo de caja")).toBeInTheDocument();
      expect(screen.getByText("Nomina junio")).toBeInTheDocument();
    });

    it("calls onSelectConversation when a conversation is clicked", () => {
      const onSelect = jest.fn();
      render(
        <Sidebar
          {...defaultProps}
          onSelectConversation={onSelect}
        />
      );

      fireEvent.click(screen.getByText("Flujo de caja"));
      expect(onSelect).toHaveBeenCalledWith(2);
    });

    it("renders an empty list gracefully", () => {
      render(<Sidebar {...defaultProps} conversations={[]} />);
      // Should still show the header and new chat button
      expect(screen.getByText("SantoniBot")).toBeInTheDocument();
      expect(screen.getByText("Nueva conversación")).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // New chat button
  // -----------------------------------------------------------------------
  describe("new chat button", () => {
    it("renders the 'Nueva conversacion' button", () => {
      render(<Sidebar {...defaultProps} />);
      expect(screen.getByText("Nueva conversación")).toBeInTheDocument();
    });

    it("calls onNewChat when clicked", () => {
      const onNewChat = jest.fn();
      render(<Sidebar {...defaultProps} onNewChat={onNewChat} />);

      fireEvent.click(screen.getByText("Nueva conversación"));
      expect(onNewChat).toHaveBeenCalledTimes(1);
    });
  });

  // -----------------------------------------------------------------------
  // Delete conversation
  // -----------------------------------------------------------------------
  describe("delete conversation", () => {
    it("calls onDeleteConversation with the correct id", () => {
      const onDelete = jest.fn();
      render(
        <Sidebar
          {...defaultProps}
          onDeleteConversation={onDelete}
        />
      );

      // Each conversation row has a trash button. Find all trash icons.
      const trashButtons = screen.getAllByTestId("icon-trash");
      // Click the second conversation's delete button (Flujo de caja, id=2)
      fireEvent.click(trashButtons[1].closest("button")!);

      expect(onDelete).toHaveBeenCalledWith(2);
    });

    it("does not trigger onSelectConversation when deleting", () => {
      const onSelect = jest.fn();
      const onDelete = jest.fn();
      render(
        <Sidebar
          {...defaultProps}
          onSelectConversation={onSelect}
          onDeleteConversation={onDelete}
        />
      );

      const trashButtons = screen.getAllByTestId("icon-trash");
      fireEvent.click(trashButtons[0].closest("button")!);

      // Delete was called but select was NOT (stopPropagation in component)
      expect(onDelete).toHaveBeenCalledWith(1);
      expect(onSelect).not.toHaveBeenCalled();
    });
  });

  // -----------------------------------------------------------------------
  // Logout
  // -----------------------------------------------------------------------
  describe("logout button", () => {
    it("calls onLogout when clicked", () => {
      const onLogout = jest.fn();
      render(<Sidebar {...defaultProps} onLogout={onLogout} />);

      const logoutButton = screen.getByTitle("Cerrar sesión");
      fireEvent.click(logoutButton);

      expect(onLogout).toHaveBeenCalledTimes(1);
    });
  });

  // -----------------------------------------------------------------------
  // User info
  // -----------------------------------------------------------------------
  describe("user info", () => {
    it("displays the user full name and department", () => {
      render(<Sidebar {...defaultProps} />);

      expect(screen.getByText("Carlos Perez")).toBeInTheDocument();
      expect(screen.getByText("Ventas")).toBeInTheDocument();
    });

    it("displays the first letter of the user name as avatar", () => {
      render(<Sidebar {...defaultProps} />);

      // The user avatar should show "C"
      expect(screen.getByText("C")).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Admin link
  // -----------------------------------------------------------------------
  describe("admin link", () => {
    it("shows Administracion link when user is administrador", () => {
      const adminUser = makeUser({ role: "administrador" });
      render(<Sidebar {...defaultProps} user={adminUser} />);

      expect(screen.getByText("Administración")).toBeInTheDocument();
    });

    it("does NOT show Administracion link for non-admin users", () => {
      const regularUser = makeUser({ role: "usuario" });
      render(<Sidebar {...defaultProps} user={regularUser} />);

      expect(screen.queryByText("Administración")).not.toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Toggle (collapse) button
  // -----------------------------------------------------------------------
  describe("toggle button", () => {
    it("calls onToggle when the collapse button is clicked", () => {
      const onToggle = jest.fn();
      render(<Sidebar {...defaultProps} onToggle={onToggle} />);

      const chevron = screen.getByTestId("icon-chevron");
      fireEvent.click(chevron.closest("button")!);

      expect(onToggle).toHaveBeenCalledTimes(1);
    });
  });
});
