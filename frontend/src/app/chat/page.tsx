"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import Sidebar from "@/components/layout/Sidebar";
import ChatWindow from "@/components/chat/ChatWindow";
import type { ConversationListItem, Message } from "@/types";
import { api } from "@/lib/api";

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
    } catch {
      // ignore
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
  };

  const handleSendMessage = async (content: string) => {
    // Optimistically add user message
    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content,
      agent_used: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const response = await api.sendMessage(
        content,
        activeConversationId ?? undefined
      );

      // Update conversation ID if new
      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id);
      }

      // Add assistant message
      const assistantMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.message,
        agent_used: response.agent_used,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh sidebar
      loadConversations();
    } catch (err) {
      const errorMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content:
          "Lo siento, ocurrió un error al procesar tu consulta. Por favor intenta de nuevo.",
        agent_used: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
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
        onSendMessage={handleSendMessage}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />
    </div>
  );
}
