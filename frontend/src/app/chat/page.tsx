"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import Sidebar from "@/components/layout/Sidebar";
import ChatWindow from "@/components/chat/ChatWindow";
import type { ConversationListItem, Message } from "@/types";
import { api } from "@/lib/api";

/**
 * Generate an auto-title from the user's first message.
 * Takes the first 50 characters and appends "..." if truncated.
 */
function generateAutoTitle(content: string): string {
  const cleaned = content.replace(/\n/g, " ").trim();
  if (cleaned.length <= 50) return cleaned;
  // Cut at last space before 50 chars for cleaner truncation
  const truncated = cleaned.slice(0, 50);
  const lastSpace = truncated.lastIndexOf(" ");
  if (lastSpace > 30) {
    return truncated.slice(0, lastSpace) + "...";
  }
  return truncated + "...";
}

export default function ChatPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [conversations, setConversations] = useState<ConversationListItem[]>(
    []
  );
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // Track whether this is the first exchange in a new conversation
  const isNewConversationRef = useRef(true);
  const firstUserMessageRef = useRef<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (user) {
      loadConversations();
    }
  }, [user]);

  const loadConversations = async () => {
    try {
      const data = await api.getConversations();
      setConversations(data);
    } catch {
      // ignore
    }
  };

  const loadConversation = async (id: number) => {
    try {
      const conv = await api.getConversation(id);
      setActiveConversationId(id);
      setMessages(conv.messages);
      // Not a new conversation
      isNewConversationRef.current = false;
      firstUserMessageRef.current = null;
    } catch {
      // ignore
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    isNewConversationRef.current = true;
    firstUserMessageRef.current = null;
  };

  const handleSendMessage = async (content: string) => {
    // Track if this is the first message for auto-title
    const isFirstMessage = isNewConversationRef.current && messages.length === 0;
    if (isFirstMessage) {
      firstUserMessageRef.current = content;
    }

    // Optimistically add user message
    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content,
      agent_used: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await api.sendMessage(
        content,
        activeConversationId ?? undefined
      );

      // Update conversation ID if new
      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id);
      }

      // Add assistant message (use real DB ID for export)
      const assistantMsg: Message = {
        id: response.message_id,
        role: "assistant",
        content: response.message,
        agent_used: response.agent_used,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Auto-generate title for new conversations after first bot response
      if (isFirstMessage && firstUserMessageRef.current) {
        const autoTitle = generateAutoTitle(firstUserMessageRef.current);
        // Try to update the title on the server
        try {
          await api.updateConversationTitle(
            response.conversation_id,
            autoTitle
          );
        } catch {
          // If server update fails, we still update locally
        }
        // Update the conversation title in the sidebar list locally
        setConversations((prev) => {
          const existing = prev.find(
            (c) => c.id === response.conversation_id
          );
          if (existing) {
            return prev.map((c) =>
              c.id === response.conversation_id
                ? {
                    ...c,
                    title: autoTitle,
                    last_message_preview: response.message.slice(0, 80),
                    updated_at: new Date().toISOString(),
                  }
                : c
            );
          }
          // New conversation - add it to the top
          return [
            {
              id: response.conversation_id,
              title: autoTitle,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              message_count: 2,
              last_message_preview: response.message.slice(0, 80),
            },
            ...prev,
          ];
        });

        isNewConversationRef.current = false;
        firstUserMessageRef.current = null;
      } else {
        // Update the last message preview for existing conversations
        setConversations((prev) =>
          prev.map((c) =>
            c.id === (activeConversationId || response.conversation_id)
              ? {
                  ...c,
                  last_message_preview: response.message.slice(0, 80),
                  updated_at: new Date().toISOString(),
                  message_count: c.message_count + 2,
                }
              : c
          )
        );
      }

      // Refresh sidebar to get any server-side updates
      loadConversations();
    } catch (err: unknown) {
      let detail = "Error desconocido";
      if (err && typeof err === "object" && "message" in err) {
        detail = (err as { message: string }).message;
      }
      const errorMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content:
          `Lo siento, ocurrio un error al procesar tu consulta: ${detail}`,
        agent_used: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteConversation = async (id: number) => {
    try {
      await api.deleteConversation(id);
      if (activeConversationId === id) {
        handleNewChat();
      }
      loadConversations();
    } catch {
      // ignore
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-12 h-12 border-4 border-santoni-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <Sidebar
        user={user}
        conversations={conversations}
        activeId={activeConversationId}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onNewChat={handleNewChat}
        onSelectConversation={loadConversation}
        onDeleteConversation={handleDeleteConversation}
        onLogout={handleLogout}
      />

      {/* Main chat area */}
      <ChatWindow
        messages={messages}
        user={user}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />
    </div>
  );
}
