"use client";

import { useState, useRef, useEffect } from "react";
import type { Message, User } from "@/types";
import ChatMessage from "./ChatMessage";
import { Send, Menu, Keyboard, Paperclip, X, FileText, LayoutDashboard, Settings } from "lucide-react";
import Link from "next/link";

interface ChatWindowProps {
  messages: Message[];
  user: User;
  isLoading: boolean;
  onSendMessage: (content: string, file?: File) => Promise<void>;
  onToggleSidebar: () => void;
}

const AGENT_LABELS: Record<string, string> = {
  finanzas: "Agente de Finanzas",
  contabilidad: "Agente de Contabilidad",
  ventas: "Agente de Ventas",
  rrhh: "Agente de RRHH",
  produccion: "Agente de Producción",
  compras_insumos: "Agente de Compras Insumos",
  compras_productores: "Agente de Compras Productores",
  general: "Asistente General",
  orchestrator: "Sistema",
};

const DEPARTMENT_SUGGESTIONS: Record<string, string[]> = {
  finanzas: [
    "¿Cuál es el flujo de caja del mes?",
    "Muéstrame las cuentas por cobrar vencidas",
    "¿Cuál es el saldo de bancos hoy?",
    "Resumen de cuentas por pagar",
  ],
  contabilidad: [
    "Muéstrame el balance general actualizado",
    "¿Cuál es el estado de resultados del mes?",
    "Resumen del libro mayor",
    "Balance de comprobación actualizado",
  ],
  ventas: [
    "¿Cuáles son los top 20 clientes por ventas?",
    "Resumen de ventas del mes por zona",
    "¿Cuánto se ha cobrado esta semana?",
    "Ranking de vendedores del mes",
  ],
  rrhh: [
    "¿Cuántos empleados hay por departamento?",
    "Resumen de nómina del mes",
    "¿Quiénes tienen asistencia pendiente?",
    "Reporte de vacaciones pendientes",
  ],
  produccion: [
    "¿Cuál es la producción de hoy?",
    "Muéstrame la eficiencia de la línea",
    "¿Cuánto desperdicio hubo esta semana?",
    "Resumen de producción mensual",
  ],
  compras_insumos: [
    "¿Cuánto se compró de insumos este mes?",
    "Órdenes de compra pendientes",
    "Top proveedores por monto de compra",
    "Resumen de compras de la semana",
  ],
  compras_productores: [
    "¿Cuánto es la compra de arroz paddy este año?",
    "Compras de maíz del mes actual",
    "Top productores por volumen",
    "Resumen de compras a productores",
  ],
};

const DEFAULT_SUGGESTIONS = [
  "¿Cuáles son los top 20 clientes por ventas?",
  "¿Cuánto es la compra de arroz paddy este año?",
  "Muéstrame el flujo de caja del mes",
  "¿Cuántos empleados hay por departamento?",
];

const MAX_CHARS = 2000;

export default function ChatWindow({
  messages,
  user,
  isLoading,
  onSendMessage,
  onToggleSidebar,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending || isLoading) return;

    const fileToSend = attachedFile;
    setInput("");
    setAttachedFile(null);
    setSending(true);
    try {
      await onSendMessage(trimmed, fileToSend || undefined);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // 10MB limit
    if (file.size > 10 * 1024 * 1024) {
      alert("El archivo es muy grande. Máximo 10MB.");
      return;
    }
    setAttachedFile(file);
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= MAX_CHARS) {
      setInput(value);
    }
  };

  const suggestions =
    DEPARTMENT_SUGGESTIONS[user.department] || DEFAULT_SUGGESTIONS;

  const isBusy = sending || isLoading;
  const charCount = input.length;
  const charWarning = charCount > MAX_CHARS * 0.8;
  const charDanger = charCount > MAX_CHARS * 0.95;

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="h-14 border-b border-gray-200 bg-white flex items-center px-4 gap-3 shrink-0">
        <button
          onClick={onToggleSidebar}
          className="text-gray-500 hover:text-gray-700 lg:hidden"
        >
          <Menu size={20} />
        </button>
        <img src="/santoni-logo.png" alt="Santoni" className="h-8 w-auto" />
        <div className="flex-1">
          <h1 className="text-sm font-semibold text-gray-900">SantoniBot</h1>
          <p className="text-xs text-gray-500">
            Asistente inteligente de Alimentos Santoni
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Link
            href="/dashboard"
            className="p-2 rounded-lg text-gray-400 hover:text-santoni-600 hover:bg-santoni-50 transition-colors"
            title="Dashboard"
          >
            <LayoutDashboard size={18} />
          </Link>
          {user.role === "administrador" && (
            <Link
              href="/admin"
              className="p-2 rounded-lg text-gray-400 hover:text-santoni-600 hover:bg-santoni-50 transition-colors"
              title="Administración"
            >
              <Settings size={18} />
            </Link>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-24 h-24 bg-santoni-100 rounded-2xl flex items-center justify-center mx-auto mb-4 p-3">
                <img src="/santoni-logo.png" alt="Santoni" className="max-h-full max-w-full object-contain" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Bienvenido a SantoniBot
              </h2>
              <p className="text-gray-500 mb-6">
                Haz una consulta sobre tu departamento. Estas son algunas
                sugerencias:
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInput(suggestion);
                      inputRef.current?.focus();
                    }}
                    className="text-left p-3 rounded-lg border border-gray-200 hover:bg-santoni-50 hover:border-santoni-300 transition-colors text-gray-600"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            userName={user.full_name}
            agentLabel={
              msg.agent_used
                ? AGENT_LABELS[msg.agent_used] || msg.agent_used
                : undefined
            }
          />
        ))}

        {/* Typing indicator with bouncing dots */}
        {isBusy && (
          <div className="flex gap-3 message-animate">
            <div className="w-8 h-8 bg-santoni-600 rounded-full flex items-center justify-center shrink-0 text-xs font-bold text-white">
              S
            </div>
            <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-santoni-400 rounded-full typing-dot" />
                <div className="w-2 h-2 bg-santoni-400 rounded-full typing-dot" />
                <div className="w-2 h-2 bg-santoni-400 rounded-full typing-dot" />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Procesando consulta...
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-4">
        {/* File attachment preview */}
        {attachedFile && (
          <div className="max-w-4xl mx-auto mb-2">
            <div className="inline-flex items-center gap-2 bg-santoni-50 border border-santoni-200 rounded-lg px-3 py-1.5 text-sm">
              <FileText size={14} className="text-santoni-600" />
              <span className="text-gray-700 truncate max-w-[200px]">
                {attachedFile.name}
              </span>
              <span className="text-gray-400 text-xs">
                ({formatFileSize(attachedFile.size)})
              </span>
              <button
                onClick={() => setAttachedFile(null)}
                className="text-gray-400 hover:text-red-500 transition-colors ml-1"
                title="Quitar archivo"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="flex items-end gap-2 max-w-4xl mx-auto"
        >
          {/* Attach file button */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.xlsx,.xls,.csv,.txt,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp"
            onChange={handleFileSelect}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isBusy}
            className="p-3 rounded-xl text-gray-400 hover:text-santoni-600 hover:bg-santoni-50 transition-colors disabled:opacity-50"
            title="Adjuntar documento"
          >
            <Paperclip size={18} />
          </button>

          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={attachedFile ? "Escribe tu consulta sobre el documento..." : "Escribe tu consulta..."}
              rows={1}
              className="input-field resize-none pr-4 max-h-32"
              style={{ minHeight: "44px" }}
              disabled={isBusy}
            />
            {/* Character count */}
            {charCount > 0 && (
              <span
                className={`absolute right-3 bottom-1.5 text-xs select-none ${
                  charDanger
                    ? "text-red-500 font-medium"
                    : charWarning
                    ? "text-amber-500"
                    : "text-gray-300"
                }`}
              >
                {charCount}/{MAX_CHARS}
              </span>
            )}
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isBusy}
            className="btn-primary p-3 rounded-xl"
            title="Enviar mensaje"
          >
            {isBusy ? (
              <div className="w-[18px] h-[18px] border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </form>
        <div className="flex items-center justify-between max-w-4xl mx-auto mt-2 px-1">
          <p className="text-xs text-gray-400 flex items-center gap-1">
            <Keyboard size={12} />
            <span>
              <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">
                Enter
              </kbd>{" "}
              enviar &middot;{" "}
              <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">
                Shift+Enter
              </kbd>{" "}
              nueva linea
            </span>
          </p>
          <p className="text-xs text-gray-400">
            SantoniBot puede cometer errores. Verifica la información.
          </p>
        </div>
      </div>
    </div>
  );
}
