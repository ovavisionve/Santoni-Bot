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
  const { user, loading, logout, inactivityWarning, resetActivity } = useAuth();
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

  const handleSendMessage = async (content: string, file?: File) => {
    // Track if this is the first message for auto-title
    const isFirstMessage = isNewConversationRef.current && messages.length === 0;
    if (isFirstMessage) {
      firstUserMessageRef.current = content;
    }

    // Optimistically add user message (show file name if attached)
    const displayContent = file
      ? `${content}\n\n📎 ${file.name}`
      : content;
    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content: displayContent,
      agent_used: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // Upload file first if attached
      let fileId: string | undefined;
      if (file) {
        try {
          const uploadResult = await api.uploadDocument(file);
          fileId = uploadResult.file_id;
        } catch (err: unknown) {
          let detail = "Error al subir archivo";
          if (err && typeof err === "object" && "message" in err) {
            detail = (err as { message: string }).message;
          }
          const errorMsg: Message = {
            id: Date.now() + 1,
            role: "assistant",
            content: `Error al adjuntar documento: ${detail}`,
            agent_used: null,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errorMsg]);
          setIsLoading(false);
          return;
        }
      }

      // Use streaming for text queries, regular for file uploads
      if (!fileId) {
        // ── STREAMING MODE ──
        const placeholderId = Date.now() + 1;
        let streamedAgent: string | null = null;

        // Add placeholder assistant message
        setMessages((prev) => [...prev, {
          id: placeholderId,
          role: "assistant" as const,
          content: "",
          agent_used: null,
          created_at: new Date().toISOString(),
        }]);
        setIsLoading(false); // Hide spinner – tokens are visible now

        const result = await api.streamMessage(
          content,
          {
            onToken: (token) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === placeholderId
                    ? { ...m, content: m.content + token }
                    : m
                )
              );
            },
            onMeta: (meta) => {
              if (!activeConversationId) {
                setActiveConversationId(meta.conversation_id);
              }
              streamedAgent = meta.agent;
            },
            onError: (error) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === placeholderId
                    ? { ...m, content: m.content + `\n\nError: ${error}` }
                    : m
                )
              );
            },
          },
          activeConversationId ?? undefined,
        );

        // Update message with real DB id + agent
        setMessages((prev) =>
          prev.map((m) =>
            m.id === placeholderId
              ? { ...m, id: result.message_id, agent_used: streamedAgent }
              : m
          )
        );

        // Auto-title + sidebar update
        await _updateSidebar(isFirstMessage, result.conversation_id, streamedAgent);

      } else {
        // ── REGULAR MODE (file upload) ──
        const response = await api.sendMessage(
          content,
          activeConversationId ?? undefined,
          fileId
        );

        if (!activeConversationId) {
          setActiveConversationId(response.conversation_id);
        }

        const assistantMsg: Message = {
          id: response.message_id,
          role: "assistant",
          content: response.message,
          agent_used: response.agent_used,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        await _updateSidebar(isFirstMessage, response.conversation_id, response.agent_used);
      }
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

  /** Helper: update sidebar after a bot response */
  const _updateSidebar = async (isFirstMessage: boolean, convId: number, _agent: string | null) => {
    if (isFirstMessage && firstUserMessageRef.current) {
      const autoTitle = generateAutoTitle(firstUserMessageRef.current);
      try { await api.updateConversationTitle(convId, autoTitle); } catch {}
      setConversations((prev) => {
        const existing = prev.find((c) => c.id === convId);
        if (existing) {
          return prev.map((c) =>
            c.id === convId ? { ...c, title: autoTitle, updated_at: new Date().toISOString() } : c
          );
        }
        return [
          { id: convId, title: autoTitle, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), message_count: 2 },
          ...prev,
        ];
      });
      isNewConversationRef.current = false;
      firstUserMessageRef.current = null;
    }
    loadConversations();
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
    <div className="h-screen flex overflow-hidden bg-gray-50 relative">
      {/* Inactivity warning banner */}
      {inactivityWarning && (
        <div className="absolute top-0 left-0 right-0 z-50 bg-yellow-500 text-white text-center py-2 px-4 text-sm font-medium shadow-lg animate-pulse">
          Tu sesion se cerrara en 5 minutos por inactividad.{" "}
          <button
            onClick={resetActivity}
            className="underline font-bold hover:text-yellow-100 ml-2"
          >
            Continuar sesion
          </button>
        </div>
      )}

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
