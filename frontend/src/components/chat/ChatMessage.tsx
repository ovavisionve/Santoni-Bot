"use client";

import type { Message } from "@/types";
import ReactMarkdown from "react-markdown";
import { Download, FileText, Table2, FileSpreadsheet } from "lucide-react";

interface ChatMessageProps {
  message: Message;
  userName: string;
  agentLabel?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function downloadExport(messageId: number, format: string) {
  const token = localStorage.getItem("santonibot_token");
  if (!token) return;

  const url = `${API_BASE}/api/export/message/${messageId}?format=${format}`;
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => res.blob())
    .then((blob) => {
      const ext = format === "excel" ? "xlsx" : format;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `santonibot_reporte.${ext}`;
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(() => alert("Error al exportar"));
}

export default function ChatMessage({
  message,
  userName,
  agentLabel,
}: ChatMessageProps) {
  const isUser = message.role === "user";
  const hasTable = !isUser && message.content.includes("|");

  return (
    <div
      className={`flex gap-3 message-animate ${
        isUser ? "flex-row-reverse" : ""
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
          isUser ? "bg-gray-700 text-white" : "bg-santoni-600 text-white"
        }`}
      >
        {isUser ? userName.charAt(0).toUpperCase() : "S"}
      </div>

      {/* Message bubble */}
      <div
        className={`max-w-[75%] ${
          isUser
            ? "bg-santoni-600 text-white rounded-2xl rounded-tr-sm"
            : "bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm"
        } px-4 py-3`}
      >
        {/* Agent badge */}
        {!isUser && agentLabel && (
          <div className="text-xs text-santoni-600 font-medium mb-1">
            {agentLabel}
          </div>
        )}

        {/* Content */}
        <div
          className={`text-sm leading-relaxed ${
            isUser ? "text-white" : "text-gray-800"
          } prose prose-sm max-w-none ${isUser ? "prose-invert" : ""}`}
        >
          {isUser ? (
            <p className="m-0">{message.content}</p>
          ) : (
            <ReactMarkdown
              components={{
                table: ({ children }) => (
                  <div className="overflow-x-auto my-2">
                    <table className="min-w-full text-xs border-collapse border border-gray-200">
                      {children}
                    </table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="border border-gray-200 bg-gray-50 px-2 py-1 text-left font-medium">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="border border-gray-200 px-2 py-1">
                    {children}
                  </td>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Export buttons + Timestamp */}
        <div
          className={`flex items-center justify-between mt-2 ${
            isUser ? "text-santoni-200" : "text-gray-400"
          }`}
        >
          <span className="text-xs">
            {new Date(message.created_at).toLocaleTimeString("es-VE", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>

          {/* Export buttons for assistant messages with data */}
          {!isUser && hasTable && (
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400 mr-1">
                <Download size={12} />
              </span>
              <button
                onClick={() => downloadExport(message.id, "csv")}
                className="text-xs text-gray-400 hover:text-santoni-600 transition-colors px-1"
                title="Exportar CSV"
              >
                <Table2 size={14} />
              </button>
              <button
                onClick={() => downloadExport(message.id, "excel")}
                className="text-xs text-gray-400 hover:text-green-600 transition-colors px-1"
                title="Exportar Excel"
              >
                <FileSpreadsheet size={14} />
              </button>
              <button
                onClick={() => downloadExport(message.id, "pdf")}
                className="text-xs text-gray-400 hover:text-red-600 transition-colors px-1"
                title="Exportar PDF"
              >
                <FileText size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
