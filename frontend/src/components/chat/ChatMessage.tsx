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
  BarChart3,
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
  return date.toLocaleDateString("es-VE", { day: "2-digit", month: "short" });
}

/**
 * Parse a numeric string, stripping currency symbols, thousand separators, etc.
 * "1,234.56" → 1234.56, "Bs. 50.000,00" → 50000, "85.3%" → 85.3
 */
function parseNumber(raw: string): number | null {
  if (!raw) return null;
  let s = raw.trim();
  // Remove currency prefixes and % suffix
  s = s.replace(/^(Bs\.?\s*|USD?\s*|\$\s*)/i, "").replace(/%$/, "");
  // Detect format: if has both . and , check which is the decimal separator
  // Venezuelan/European format: 1.234,56 → remove dots, replace comma with dot
  // US format: 1,234.56 → remove commas
  if (s.includes(",") && s.includes(".")) {
    if (s.lastIndexOf(",") > s.lastIndexOf(".")) {
      // Venezuelan: 1.234,56
      s = s.replace(/\./g, "").replace(",", ".");
    } else {
      // US: 1,234.56
      s = s.replace(/,/g, "");
    }
  } else if (s.includes(",")) {
    // Could be thousand sep (1,234) or decimal (0,5)
    const parts = s.split(",");
    if (parts.length === 2 && parts[1].length <= 2) {
      s = s.replace(",", "."); // decimal
    } else {
      s = s.replace(/,/g, ""); // thousand
    }
  }
  const n = parseFloat(s);
  return isNaN(n) ? null : n;
}

/**
 * Extract the FIRST markdown table from content and convert to ChartData.
 * Returns null if no suitable table found (needs 3+ data rows, at least 1 numeric column).
 */
function extractChartFromTable(content: string): ChartData | null {
  const lines = content.split("\n");
  let headerLine = -1;

  // Find the first markdown table: a line with |, followed by a separator |---|
  for (let i = 0; i < lines.length - 2; i++) {
    const line = lines[i].trim();
    const next = lines[i + 1]?.trim() || "";
    if (
      line.startsWith("|") &&
      line.endsWith("|") &&
      next.startsWith("|") &&
      /^[\s|:-]+$/.test(next)
    ) {
      headerLine = i;
      break;
    }
  }
  if (headerLine === -1) return null;

  // Parse headers
  const headers = lines[headerLine]
    .split("|")
    .map((h) => h.trim())
    .filter(Boolean);

  if (headers.length < 2) return null;

  // Parse data rows (skip separator at headerLine+1)
  const rows: string[][] = [];
  for (let i = headerLine + 2; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line.startsWith("|")) break;
    const cells = line
      .split("|")
      .map((c) => c.trim())
      .filter((_, idx, arr) => idx > 0 && idx < arr.length); // remove empty first/last from split
    if (cells.length >= 2) rows.push(cells);
  }

  if (rows.length < 3) return null; // Need at least 3 rows for a useful chart

  // Detect which columns are numeric (check all rows)
  const numericCols: number[] = [];
  for (let col = 0; col < headers.length; col++) {
    const allNumeric = rows.every((row) => {
      const val = row[col] || "";
      // Skip columns that are ordinal (#, Pos, Posición, No.)
      if (col === 0 && /^#|^pos|^no\.?$/i.test(headers[col])) return false;
      return parseNumber(val) !== null;
    });
    if (allNumeric) numericCols.push(col);
  }

  if (numericCols.length === 0) return null; // No numeric columns

  // The label column is the first non-numeric column (or col 0 if all are numeric)
  let labelCol = 0;
  for (let col = 0; col < headers.length; col++) {
    if (!numericCols.includes(col)) {
      labelCol = col;
      break;
    }
  }

  // Use at most 2 numeric columns for the chart (first two found)
  const valueCols = numericCols.slice(0, 2);
  const xKey = headers[labelCol];
  const yKey =
    valueCols.length === 1
      ? headers[valueCols[0]]
      : valueCols.map((c) => headers[c]);

  // Build data array (limit to 15 rows)
  const data = rows.slice(0, 15).map((row) => {
    const item: Record<string, unknown> = { [xKey]: row[labelCol] || "" };
    for (const vc of valueCols) {
      item[headers[vc]] = parseNumber(row[vc] || "0") ?? 0;
    }
    return item;
  });

  // Determine chart type
  let type: ChartData["type"] = "bar"; // default
  const xValues = data.map((d) => String(d[xKey]));
  const looksLikeTimeSeries = xValues.some((v) =>
    /\d{4}|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|semana|lun|mar|mie|jue|vie/i.test(
      v
    )
  );
  if (looksLikeTimeSeries) type = "line";

  // Find a title from the line before the table (## header or bold text)
  let title = "";
  for (let i = headerLine - 1; i >= Math.max(0, headerLine - 3); i--) {
    const prev = lines[i].trim();
    if (prev.startsWith("##")) {
      title = prev.replace(/^#+\s*/, "");
      break;
    }
    if (prev.startsWith("**") && prev.endsWith("**")) {
      title = prev.replace(/\*\*/g, "");
      break;
    }
    if (prev.length > 5 && prev.length < 80 && !prev.startsWith("|")) {
      title = prev.replace(/[*#:]/g, "").trim();
      break;
    }
  }

  return { type, title, xKey, yKey, data };
}

/**
 * Also try to extract ```chart JSON blocks from the LLM (bonus).
 */
function extractLLMCharts(content: string): { text: string; charts: ChartData[] } {
  const charts: ChartData[] = [];
  const text = content.replace(
    /```chart\s*([\s\S]*?)```/g,
    (_match, jsonStr: string) => {
      try {
        const trimmed = jsonStr.trim();
        const start = trimmed.indexOf("{");
        const end = trimmed.lastIndexOf("}");
        if (start === -1 || end === -1) return _match;
        const parsed = JSON.parse(trimmed.slice(start, end + 1));
        if (parsed.type && parsed.xKey && parsed.yKey && Array.isArray(parsed.data)) {
          charts.push(parsed as ChartData);
          return "";
        }
      } catch {
        // Invalid JSON
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
  const [showChart, setShowChart] = useState(false);
  const isUser = message.role === "user";
  const hasTable = !isUser && message.content.includes("|");

  // Try LLM-generated charts first, then auto-parse from tables
  const { text: messageText, charts: llmCharts } = isUser
    ? { text: message.content, charts: [] }
    : extractLLMCharts(message.content);

  const autoChart = !isUser && llmCharts.length === 0
    ? extractChartFromTable(message.content)
    : null;

  const hasChartData = llmCharts.length > 0 || autoChart !== null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
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
          isUser ? "bg-gray-700 text-white" : "bg-santoni-600 text-white p-1.5"
        }`}
      >
        {isUser ? (
          userName.charAt(0).toUpperCase()
        ) : (
          <img src="/santoni-logo.png" alt="S" className="h-full w-auto brightness-0 invert" />
        )}
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

              {/* LLM-generated charts (if any) */}
              {llmCharts.map((chart, i) => (
                <ChartRenderer key={`llm-${i}`} chart={chart} />
              ))}

              {/* Auto-generated chart from parsed table */}
              {autoChart && showChart && (
                <ChartRenderer chart={autoChart} />
              )}
            </>
          )}
        </div>

        {/* Export buttons + Chart toggle + Timestamp */}
        <div
          className={`flex items-center justify-between mt-2 ${
            isUser ? "text-santoni-200" : "text-gray-400"
          }`}
        >
          <span className="text-xs" title={new Date(message.created_at).toLocaleString("es-VE")}>
            {getRelativeTime(message.created_at)}
          </span>

          {/* Action buttons for assistant messages with data */}
          {!isUser && hasTable && (
            <div className="flex items-center gap-1">
              {/* Chart toggle button */}
              {autoChart && (
                <button
                  onClick={() => setShowChart(!showChart)}
                  className={`text-xs transition-colors px-1.5 py-0.5 rounded ${
                    showChart
                      ? "text-santoni-600 bg-santoni-50"
                      : "text-gray-400 hover:text-santoni-600"
                  }`}
                  title={showChart ? "Ocultar gráfica" : "Ver como gráfica"}
                >
                  <BarChart3 size={14} />
                </button>
              )}
              <span className="text-xs text-gray-300 mx-0.5">|</span>
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
