"use client";

import type { User, ConversationListItem } from "@/types";
import {
  MessageSquarePlus,
  LogOut,
  Trash2,
  Settings,
  MessageSquare,
  ChevronLeft,
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
  if (!isOpen) return null;

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
          Nueva conversación
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto chat-scroll px-3 space-y-1">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors text-sm ${
              activeId === conv.id
                ? "bg-gray-700 text-white"
                : "text-gray-300 hover:bg-gray-800"
            }`}
            onClick={() => onSelectConversation(conv.id)}
          >
            <MessageSquare size={14} className="shrink-0" />
            <span className="truncate flex-1">{conv.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteConversation(conv.id);
              }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition-all"
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
            Administración
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
            title="Cerrar sesión"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
