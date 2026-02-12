"use client";

import { useState } from "react";
import type { User, ConversationListItem } from "@/types";
import {
  MessageSquarePlus,
  LogOut,
  Trash2,
  Settings,
  MessageSquare,
  ChevronLeft,
  Search,
  X,
} from "lucide-react";
import Link from "next/link";

interface SidebarProps {
  user: User;
  conversations: ConversationListItem[];
  activeId: number | null;
  isOpen: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectConversation: (id: number) => void;
  onDeleteConversation: (id: number) => void;
  onLogout: () => void;
}

const DEPARTMENT_LABELS: Record<string, string> = {
  finanzas: "Finanzas",
  contabilidad: "Contabilidad",
  ventas: "Ventas",
  rrhh: "RRHH",
  produccion: "Producción",
  compras_insumos: "Compras Insumos",
  compras_productores: "Compras Productores",
};

/**
 * Returns a short Spanish relative time for the sidebar timestamps
 */
function getSidebarTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `${diffMin}m`;
  if (diffHour < 24) return `${diffHour}h`;
  if (diffDay === 1) return "ayer";
  if (diffDay < 7) return `${diffDay}d`;
  return date.toLocaleDateString("es-VE", {
    day: "2-digit",
    month: "short",
  });
}

export default function Sidebar({
  user,
  conversations,
  activeId,
  isOpen,
  onToggle,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onLogout,
}: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  if (!isOpen) return null;

  const filteredConversations = searchQuery.trim()
    ? conversations.filter((conv) =>
        conv.title.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : conversations;

  return (
    <div className="w-72 bg-gray-900 text-white flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-santoni-600 rounded-lg flex items-center justify-center">
            <span className="text-sm font-bold">S</span>
          </div>
          <span className="font-semibold">SantoniBot</span>
        </div>
        <button
          onClick={onToggle}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <ChevronLeft size={20} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-600 hover:bg-gray-800 transition-colors text-sm"
        >
          <MessageSquarePlus size={16} />
          Nueva conversacion
        </button>
      </div>

      {/* Search bar */}
      <div className="px-3 pb-2">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar conversaciones..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-8 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-santoni-500 focus:border-santoni-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto chat-scroll px-3 space-y-1">
        {filteredConversations.length === 0 && searchQuery && (
          <p className="text-xs text-gray-500 text-center py-4">
            No se encontraron conversaciones
          </p>
        )}
        {filteredConversations.length === 0 && !searchQuery && (
          <p className="text-xs text-gray-500 text-center py-4">
            Sin conversaciones aun
          </p>
        )}
        {filteredConversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-start gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors text-sm ${
              activeId === conv.id
                ? "bg-gray-700 text-white"
                : "text-gray-300 hover:bg-gray-800"
            }`}
            onClick={() => onSelectConversation(conv.id)}
          >
            <MessageSquare size={14} className="shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate flex-1 text-sm leading-tight">
                  {conv.title.length > 40
                    ? conv.title.slice(0, 40) + "..."
                    : conv.title}
                </span>
                <span className="text-[10px] text-gray-500 shrink-0">
                  {getSidebarTime(conv.updated_at)}
                </span>
              </div>
              {/* Conversation preview */}
              {conv.last_message_preview && (
                <p className="text-xs text-gray-500 truncate mt-0.5 leading-tight">
                  {conv.last_message_preview}
                </p>
              )}
              {!conv.last_message_preview && conv.message_count > 0 && (
                <p className="text-xs text-gray-500 mt-0.5 leading-tight">
                  {conv.message_count}{" "}
                  {conv.message_count === 1 ? "mensaje" : "mensajes"}
                </p>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteConversation(conv.id);
              }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-all shrink-0 mt-0.5"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* User Info & Actions */}
      <div className="border-t border-gray-700 p-3 space-y-2">
        {user.role === "administrador" && (
          <Link
            href="/admin"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-300 hover:bg-gray-800 transition-colors text-sm"
          >
            <Settings size={16} />
            Administracion
          </Link>
        )}

        <div className="flex items-center gap-3 px-3 py-2">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.full_name}
              className="w-8 h-8 rounded-full object-cover shrink-0"
            />
          ) : (
            <div className="w-8 h-8 bg-santoni-500 rounded-full flex items-center justify-center text-sm font-medium shrink-0">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user.full_name}</p>
            <p className="text-xs text-gray-400">
              {DEPARTMENT_LABELS[user.department] || user.department}
            </p>
          </div>
          <button
            onClick={onLogout}
            className="text-gray-400 hover:text-red-400 transition-colors"
            title="Cerrar sesion"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
