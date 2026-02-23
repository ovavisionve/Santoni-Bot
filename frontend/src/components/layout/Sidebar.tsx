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
  Download,
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
  onDownloadConversation: (id: number, format: "txt" | "pdf") => void;
  onDownloadAll: (format: "txt" | "pdf") => void;
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
  onDownloadConversation,
  onDownloadAll,
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
    <div className="w-72 bg-santoni-950 text-white flex flex-col h-full shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-santoni-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/santoni-logo.png" alt="Santoni" className="h-8 w-auto" />
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
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-santoni-800 hover:bg-santoni-900 transition-colors text-sm"
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
            className="w-full bg-santoni-900 border border-santoni-800 rounded-lg pl-8 pr-8 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-santoni-500 focus:border-santoni-500 transition-all"
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
                ? "bg-santoni-800 text-white"
                : "text-gray-300 hover:bg-santoni-900"
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
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-all shrink-0 mt-0.5">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDownloadConversation(conv.id, "txt");
                }}
                className="text-gray-400 hover:text-blue-400 transition-colors"
                title="Descargar TXT"
              >
                <Download size={13} />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteConversation(conv.id);
                }}
                className="text-gray-400 hover:text-red-400 transition-colors"
                title="Eliminar"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* User Info & Actions */}
      <div className="border-t border-santoni-900 p-3 space-y-2">
        {/* Download all conversations */}
        {conversations.length > 0 && (
          <div className="flex gap-1">
            <button
              onClick={() => onDownloadAll("txt")}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-gray-400 hover:text-blue-400 hover:bg-santoni-900 transition-colors text-xs border border-santoni-800"
              title="Descargar todas las conversaciones en TXT"
            >
              <Download size={13} />
              Descargar todas (TXT)
            </button>
            <button
              onClick={() => onDownloadAll("pdf")}
              className="flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-santoni-900 transition-colors text-xs border border-santoni-800"
              title="Descargar todas las conversaciones en PDF"
            >
              PDF
            </button>
          </div>
        )}

        {user.role === "administrador" && (
          <Link
            href="/admin"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-300 hover:bg-santoni-900 transition-colors text-sm"
          >
            <Settings size={16} />
            Administracion
          </Link>
        )}

        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 bg-santoni-500 rounded-full flex items-center justify-center text-sm font-medium">
            {user.full_name.charAt(0).toUpperCase()}
          </div>
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
