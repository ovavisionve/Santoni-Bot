"use client";

import { useState } from "react";
import type { Message } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Download,
  FileText,
  Table2,
  FileSpreadsheet,
  Copy,
  Check,
} from "lucide-react";
import ChartRenderer, { type ChartData } from "./ChartRenderer";

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
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      return res.blob();
    })
    .then((blob) => {
      const ext = format === "excel" ? "xlsx" : format;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `santonibot_reporte.${ext}`;
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch((err) => alert(`Error al exportar: ${err.message}`));
}

/**
 * Returns a Spanish relative time string like "ahora", "hace 5 min", "hace 2h", "ayer"
 */
function getRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "ahora";
  if (diffMin === 1) return "hace 1 min";
  if (diffMin < 60) return `hace ${diffMin} min`;
  if (diffHour === 1) return "hace 1 hora";
  if (diffHour < 24) return `hace ${diffHour}h`;
  if (diffDay === 1) return "ayer";
  if (diffDay < 7) return `hace ${diffDay} dias`;
  return date.toLocaleDateString("es-VE", {
    day: "2-digit",
    month: "short",
  });
}

/**
 * Extracts ```chart JSON blocks from message content.
 * Returns the charts and the remaining markdown text.
 */
function extractCharts(content: string): { text: string; charts: ChartData[] } {
  const charts: ChartData[] = [];
  // Match ```chart with optional whitespace/newline, then JSON, then closing ```
  const text = content.replace(
    /```chart\s*([\s\S]*?)```/g,
    (_match, jsonStr: string) => {
      try {
        const trimmed = jsonStr.trim();
        // Find the JSON object boundaries
        const start = trimmed.indexOf("{");
        const end = trimmed.lastIndexOf("}");
        if (start === -1 || end === -1) return _match;
        const parsed = JSON.parse(trimmed.slice(start, end + 1));
        if (parsed.type && parsed.xKey && parsed.yKey && Array.isArray(parsed.data)) {
          charts.push(parsed as ChartData);
          return "";
        }
      } catch {
        // Invalid JSON — leave as text
      }
      return _match;
    }
  );
  return { text: text.trim(), charts };
}

export default function ChatMessage({
  message,
  userName,
  agentLabel,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const hasTable = !isUser && message.content.includes("|");

  // Parse charts from assistant messages
  const { text: messageText, charts } = isUser
    ? { text: message.content, charts: [] }
    : extractCharts(message.content);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = message.content;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

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
        className={`message-bubble group relative max-w-[75%] ${
          isUser
            ? "bg-santoni-600 text-white rounded-2xl rounded-tr-sm"
            : "bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm"
        } px-4 py-3`}
      >
        {/* Copy button for assistant messages */}
        {!isUser && (
          <button
            onClick={handleCopy}
            className="copy-btn absolute top-2 right-2 p-1.5 rounded-md bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-400 hover:text-gray-600 transition-all"
            title={copied ? "Copiado" : "Copiar respuesta"}
          >
            {copied ? (
              <Check size={13} className="text-green-500" />
            ) : (
              <Copy size={13} />
            )}
          </button>
        )}

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
            <>
              {messageText && (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    table: ({ children }) => (
                      <div className="overflow-x-auto my-3 rounded-lg border border-gray-200">
                        <table className="min-w-full text-xs border-collapse">
                          {children}
                        </table>
                      </div>
                    ),
                    thead: ({ children }) => (
                      <thead className="bg-santoni-50">{children}</thead>
                    ),
                    th: ({ children }) => (
                      <th className="border-b border-gray-200 px-3 py-2 text-left font-semibold text-gray-700 text-xs whitespace-nowrap">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="border-b border-gray-100 px-3 py-1.5 text-xs">
                        {children}
                      </td>
                    ),
                    tr: ({ children, ...props }) => (
                      <tr className="hover:bg-gray-50 transition-colors" {...props}>
                        {children}
                      </tr>
                    ),
                  }}
                >
                  {messageText}
                </ReactMarkdown>
              )}
              {charts.map((chart, i) => (
                <ChartRenderer key={i} chart={chart} />
              ))}
            </>
          )}
        </div>

        {/* Export buttons + Timestamp */}
        <div
          className={`flex items-center justify-between mt-2 ${
            isUser ? "text-santoni-200" : "text-gray-400"
          }`}
        >
          <span className="text-xs" title={new Date(message.created_at).toLocaleString("es-VE")}>
            {getRelativeTime(message.created_at)}
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
