/**
 * Tests for the ChatMessage component.
 *
 * Covers:
 * - Renders a user message with the user's initial
 * - Renders an assistant message with the SantoniBot "S" avatar
 * - Shows agent badge when agentLabel is provided
 * - Renders markdown content (bold, lists) via ReactMarkdown
 * - Shows export buttons (CSV, Excel, PDF) when message contains a table
 * - Does NOT show export buttons for user messages or messages without tables
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import ChatMessage from "@/components/chat/ChatMessage";
import type { Message } from "@/types";

// ---------------------------------------------------------------------------
// Mock react-markdown so tests don't depend on its internals.
// We render children as-is inside a <div data-testid="markdown">.
// ---------------------------------------------------------------------------
jest.mock("react-markdown", () => {
  return function MockReactMarkdown({
    children,
  }: {
    children: string;
  }) {
    return <div data-testid="markdown">{children}</div>;
  };
});

// Mock lucide-react icons to simple spans so we can detect them
jest.mock("lucide-react", () => ({
  Download: (props: Record<string, unknown>) => (
    <span data-testid="icon-download" {...props} />
  ),
  FileText: (props: Record<string, unknown>) => (
    <span data-testid="icon-file-text" {...props} />
  ),
  Table2: (props: Record<string, unknown>) => (
    <span data-testid="icon-table2" {...props} />
  ),
  FileSpreadsheet: (props: Record<string, unknown>) => (
    <span data-testid="icon-file-spreadsheet" {...props} />
  ),
}));

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: 1,
    role: "user",
    content: "Hola, necesito un reporte",
    agent_used: null,
    created_at: "2025-06-15T14:30:00Z",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ChatMessage", () => {
  // -----------------------------------------------------------------------
  // User messages
  // -----------------------------------------------------------------------
  describe("user message", () => {
    it("renders the message content as plain text", () => {
      const msg = makeMessage({ role: "user", content: "Hola mundo" });
      render(<ChatMessage message={msg} userName="Carlos Perez" />);

      expect(screen.getByText("Hola mundo")).toBeInTheDocument();
    });

    it("shows the first letter of the user name as avatar", () => {
      const msg = makeMessage({ role: "user" });
      render(<ChatMessage message={msg} userName="Carlos Perez" />);

      // The avatar should contain "C"
      expect(screen.getByText("C")).toBeInTheDocument();
    });

    it("does NOT render markdown for user messages", () => {
      const msg = makeMessage({ role: "user", content: "**bold text**" });
      render(<ChatMessage message={msg} userName="Test User" />);

      // ReactMarkdown mock renders into data-testid="markdown"; it should NOT be present
      expect(screen.queryByTestId("markdown")).not.toBeInTheDocument();
    });

    it("does NOT show export buttons", () => {
      const msg = makeMessage({
        role: "user",
        content: "| col1 | col2 |\n| --- | --- |\n| a | b |",
      });
      render(<ChatMessage message={msg} userName="Test" />);

      expect(screen.queryByTitle("Exportar CSV")).not.toBeInTheDocument();
      expect(screen.queryByTitle("Exportar Excel")).not.toBeInTheDocument();
      expect(screen.queryByTitle("Exportar PDF")).not.toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Assistant messages
  // -----------------------------------------------------------------------
  describe("assistant message", () => {
    it("renders content via ReactMarkdown", () => {
      const msg = makeMessage({
        role: "assistant",
        content: "Aqui esta el reporte",
        agent_used: "ventas",
      });
      render(
        <ChatMessage
          message={msg}
          userName="Admin"
          agentLabel="Agente de Ventas"
        />
      );

      // The mocked ReactMarkdown wraps content in data-testid="markdown"
      const md = screen.getByTestId("markdown");
      expect(md).toHaveTextContent("Aqui esta el reporte");
    });

    it("shows the SantoniBot 'S' avatar", () => {
      const msg = makeMessage({ role: "assistant", content: "Respuesta" });
      render(<ChatMessage message={msg} userName="Admin" />);

      expect(screen.getByText("S")).toBeInTheDocument();
    });

    it("displays the agent badge when agentLabel is provided", () => {
      const msg = makeMessage({
        role: "assistant",
        content: "Datos financieros",
        agent_used: "finanzas",
      });
      render(
        <ChatMessage
          message={msg}
          userName="Admin"
          agentLabel="Agente de Finanzas"
        />
      );

      expect(screen.getByText("Agente de Finanzas")).toBeInTheDocument();
    });

    it("does NOT display agent badge when agentLabel is not provided", () => {
      const msg = makeMessage({
        role: "assistant",
        content: "Respuesta general",
        agent_used: null,
      });
      render(<ChatMessage message={msg} userName="Admin" />);

      expect(
        screen.queryByText(/^Agente de/)
      ).not.toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Export buttons (only for assistant messages containing tables)
  // -----------------------------------------------------------------------
  describe("export buttons", () => {
    it("shows CSV, Excel, and PDF export buttons when message has a table", () => {
      const tableContent =
        "| Cliente | Monto |\n| --- | --- |\n| Acme | 1000 |";
      const msg = makeMessage({
        id: 99,
        role: "assistant",
        content: tableContent,
        agent_used: "ventas",
      });
      render(
        <ChatMessage
          message={msg}
          userName="Admin"
          agentLabel="Agente de Ventas"
        />
      );

      expect(screen.getByTitle("Exportar CSV")).toBeInTheDocument();
      expect(screen.getByTitle("Exportar Excel")).toBeInTheDocument();
      expect(screen.getByTitle("Exportar PDF")).toBeInTheDocument();
    });

    it("does NOT show export buttons when assistant message has no table", () => {
      const msg = makeMessage({
        role: "assistant",
        content: "No hay datos tabulares aqui.",
        agent_used: "ventas",
      });
      render(
        <ChatMessage
          message={msg}
          userName="Admin"
          agentLabel="Agente de Ventas"
        />
      );

      expect(screen.queryByTitle("Exportar CSV")).not.toBeInTheDocument();
      expect(screen.queryByTitle("Exportar Excel")).not.toBeInTheDocument();
      expect(screen.queryByTitle("Exportar PDF")).not.toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Timestamp
  // -----------------------------------------------------------------------
  describe("timestamp", () => {
    it("renders a formatted time string from created_at", () => {
      const msg = makeMessage({
        role: "assistant",
        content: "Hola",
        created_at: "2025-06-15T14:30:00Z",
      });
      const { container } = render(
        <ChatMessage message={msg} userName="Admin" />
      );

      // The timestamp is rendered; the exact format depends on locale.
      // We just check that some time-like text is present.
      const timeElements = container.querySelectorAll(".text-xs");
      const timeTexts = Array.from(timeElements).map(
        (el) => el.textContent || ""
      );
      // At least one element should contain a colon (time format HH:MM)
      expect(timeTexts.some((t) => /\d{1,2}:\d{2}/.test(t))).toBe(true);
    });
  });
});
