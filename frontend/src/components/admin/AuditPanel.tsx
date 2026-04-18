"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/types";
import {
  ArrowLeft,
  MessageSquare,
  Download,
  ChevronDown,
  ChevronUp,
  Eye,
  Search,
  Filter,
} from "lucide-react";
import { DEPARTMENT_LABELS, ROLE_LABELS } from "./constants";

export default function AuditPanel({
  auditLogs,
  users,
}: {
  auditLogs: Array<{
    id: number;
    user_id: number;
    username: string | null;
    full_name: string | null;
    action: string;
    resource: string;
    detail: string;
    agent_used: string;
    ip_address: string | null;
    created_at: string;
  }>;
  users: User[];
}) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [viewingConvs, setViewingConvs] = useState<{
    user: { id: number; username: string; full_name: string };
    conversations: Array<{
      id: number;
      title: string;
      created_at: string | null;
      message_count: number;
      messages: Array<{ role: string; content: string; agent_used: string | null; created_at: string | null }>;
    }>;
  } | null>(null);
  const [loadingConvs, setLoadingConvs] = useState(false);
  const [expandedConv, setExpandedConv] = useState<number | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [showActiveOnly, setShowActiveOnly] = useState(true);
  const [filterRole, setFilterRole] = useState<string>("all");
  const [filterDept, setFilterDept] = useState<string>("all");
  const [showFilters, setShowFilters] = useState(false);

  const handleViewConversations = async (userId: number) => {
    setLoadingConvs(true);
    try {
      const data = await api.getUserConversations(userId);
      setViewingConvs({ user: data.user, conversations: data.conversations });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al cargar conversaciones");
    } finally {
      setLoadingConvs(false);
    }
  };

  const handleDownload = (userId: number, format: "txt" | "pdf") => {
    const url = api.exportUserConversationsUrl(userId, format);
    const token = localStorage.getItem("santonibot_token");
    fetch(url, { headers: { Authorization: `Bearer ${token || ""}` } })
      .then(r => {
        if (!r.ok) throw new Error("Error al descargar");
        return r.blob();
      })
      .then(blob => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `conversaciones_${format}.${format}`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(err => alert(err.message));
  };

  if (viewingConvs) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setViewingConvs(null)}
              className="text-gray-500 hover:text-gray-700"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h2 className="text-lg font-semibold">
                Conversaciones de {viewingConvs.user.full_name}
              </h2>
              <p className="text-xs text-gray-500">@{viewingConvs.user.username} - {viewingConvs.conversations.length} conversaciones</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleDownload(viewingConvs.user.id, "txt")}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm text-gray-700 transition-colors"
            >
              <Download size={14} /> TXT
            </button>
            <button
              onClick={() => handleDownload(viewingConvs.user.id, "pdf")}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-santoni-600 hover:bg-santoni-700 rounded-lg text-sm text-white transition-colors"
            >
              <Download size={14} /> PDF
            </button>
          </div>
        </div>

        {viewingConvs.conversations.map((conv) => (
          <div key={conv.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <button
              onClick={() => setExpandedConv(expandedConv === conv.id ? null : conv.id)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50"
            >
              <div className="text-left">
                <div className="text-sm font-medium text-gray-900">{conv.title}</div>
                <div className="text-xs text-gray-500">
                  {conv.created_at ? new Date(conv.created_at).toLocaleString("es-VE") : ""} - {conv.message_count} mensajes
                </div>
              </div>
              {expandedConv === conv.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {expandedConv === conv.id && (
              <div className="border-t border-gray-100 px-4 py-3 space-y-3 bg-gray-50 max-h-96 overflow-y-auto">
                {conv.messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-lg px-3 py-2 text-xs ${
                      m.role === "user"
                        ? "bg-santoni-600 text-white"
                        : "bg-white border border-gray-200 text-gray-700"
                    }`}>
                      {m.role !== "user" && m.agent_used && (
                        <div className="text-[10px] font-medium text-santoni-500 mb-1">
                          {DEPARTMENT_LABELS[m.agent_used] || m.agent_used}
                        </div>
                      )}
                      <div className="whitespace-pre-wrap break-words">{m.content}</div>
                      {m.created_at && (
                        <div className={`text-[10px] mt-1 ${m.role === "user" ? "text-white/60" : "text-gray-400"}`}>
                          {new Date(m.created_at).toLocaleTimeString("es-VE", { hour: "2-digit", minute: "2-digit" })}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {viewingConvs.conversations.length === 0 && (
          <div className="text-center text-gray-400 py-8">Este usuario no tiene conversaciones</div>
        )}
      </div>
    );
  }

  const filteredUsers = users
    .filter((u) => {
      if (showActiveOnly && !u.is_active) return false;
      if (filterRole !== "all" && u.role !== filterRole) return false;
      if (filterDept !== "all" && u.department !== filterDept) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          u.full_name.toLowerCase().includes(q) ||
          u.username.toLowerCase().includes(q) ||
          u.email.toLowerCase().includes(q)
        );
      }
      return true;
    })
    .sort((a, b) => (b.conversation_count ?? 0) - (a.conversation_count ?? 0));

  const availableRoles = Array.from(new Set(users.map((u) => u.role)));
  const availableDepts = Array.from(new Set(users.map((u) => u.department)));

  return (
    <div className="space-y-4">
      {/* Search and filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por nombre, usuario o email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-santoni-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm transition-colors ${
              showFilters || filterRole !== "all" || filterDept !== "all" || !showActiveOnly
                ? "border-santoni-300 bg-santoni-50 text-santoni-700"
                : "border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            <Filter size={14} />
            Filtros
          </button>
          <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showActiveOnly}
              onChange={(e) => setShowActiveOnly(e.target.checked)}
              className="rounded border-gray-300 text-santoni-600 focus:ring-santoni-500"
            />
            Solo activos
          </label>
        </div>

        {showFilters && (
          <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-100">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Rol</label>
              <select
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
                className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-santoni-500"
              >
                <option value="all">Todos los roles</option>
                {availableRoles.map((r) => (
                  <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Departamento</label>
              <select
                value={filterDept}
                onChange={(e) => setFilterDept(e.target.value)}
                className="border border-gray-200 rounded-lg px-2 py-1.5 text-xs focus:ring-2 focus:ring-santoni-500"
              >
                <option value="all">Todos los departamentos</option>
                {availableDepts.map((d) => (
                  <option key={d} value={d}>{DEPARTMENT_LABELS[d] || d}</option>
                ))}
              </select>
            </div>
            {(filterRole !== "all" || filterDept !== "all") && (
              <button
                onClick={() => { setFilterRole("all"); setFilterDept("all"); }}
                className="self-end text-xs text-santoni-600 hover:text-santoni-800 underline pb-1.5"
              >
                Limpiar filtros
              </button>
            )}
          </div>
        )}
      </div>

      {/* User list with conversations */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Eye size={16} />
            Usuarios ({filteredUsers.length})
          </h3>
          <span className="text-xs text-gray-400">Ordenados por conversaciones</span>
        </div>
        <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
          {filteredUsers.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${u.is_active ? "bg-green-400" : "bg-gray-300"}`} />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{u.full_name}</div>
                  <div className="text-xs text-gray-400 truncate">
                    @{u.username} &middot; {ROLE_LABELS[u.role] || u.role} &middot; {DEPARTMENT_LABELS[u.department] || u.department}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                  {u.conversation_count ?? 0} conv.
                </span>
                <button
                  onClick={() => handleViewConversations(u.id)}
                  disabled={loadingConvs}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 bg-santoni-50 hover:bg-santoni-100 text-santoni-700 rounded-lg text-xs transition-colors disabled:opacity-50"
                  title="Ver conversaciones"
                >
                  <MessageSquare size={12} />
                  Ver chats
                </button>
                <button
                  onClick={() => handleDownload(u.id, "txt")}
                  className="flex items-center gap-1 px-2 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-600 rounded-lg text-xs transition-colors"
                  title="Exportar TXT"
                >
                  <Download size={12} /> TXT
                </button>
                <button
                  onClick={() => handleDownload(u.id, "pdf")}
                  className="flex items-center gap-1 px-2 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-600 rounded-lg text-xs transition-colors"
                  title="Exportar PDF"
                >
                  <Download size={12} /> PDF
                </button>
              </div>
            </div>
          ))}
          {filteredUsers.length === 0 && (
            <div className="px-4 py-8 text-center text-gray-400 text-sm">
              No se encontraron usuarios con los filtros aplicados
            </div>
          )}
        </div>
      </div>

      {/* Audit log table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700">Registro de actividad</h3>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Fecha</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Usuario</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Accion</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Detalle</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Agente</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">IP</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {auditLogs.map((log) => (
              <tr
                key={log.id}
                className={`hover:bg-gray-50 cursor-pointer ${
                  log.action === "access_denied" || log.action === "login_failed"
                    ? "bg-red-50"
                    : ""
                }`}
                onClick={() => setExpandedRow(expandedRow === log.id ? null : log.id)}
              >
                <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                  {new Date(log.created_at).toLocaleString("es-VE")}
                </td>
                <td className="px-4 py-3">
                  {log.username ? (
                    <div>
                      <div className="font-medium text-gray-900 text-xs">{log.full_name}</div>
                      <div className="text-gray-400 text-xs">@{log.username}</div>
                    </div>
                  ) : (
                    <span className="text-gray-400 text-xs italic">Desconocido</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    log.action === "login" ? "bg-green-100 text-green-700"
                    : log.action === "login_failed" ? "bg-red-100 text-red-700"
                    : log.action === "access_denied" ? "bg-red-100 text-red-700"
                    : log.action === "chat_query" ? "bg-blue-100 text-blue-700"
                    : "bg-gray-100 text-gray-700"
                  }`}>
                    {log.action === "login" ? "Inicio sesion"
                    : log.action === "login_failed" ? "Login fallido"
                    : log.action === "access_denied" ? "ACCESO DENEGADO"
                    : log.action === "chat_query" ? "Consulta"
                    : log.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {expandedRow === log.id ? (
                    <div className="whitespace-pre-wrap break-words max-w-lg">{log.detail}</div>
                  ) : (
                    <div className="max-w-sm truncate">{log.detail}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {log.agent_used ? DEPARTMENT_LABELS[log.agent_used] || log.agent_used : "-"}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs font-mono">
                  {log.ip_address || "-"}
                </td>
              </tr>
            ))}
            {auditLogs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No hay registros de auditoria
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
