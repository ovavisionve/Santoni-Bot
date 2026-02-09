"use client";

import { useState, useRef, useEffect } from "react";
import type { Message, User } from "@/types";
import ChatMessage from "./ChatMessage";
import { Send, Menu } from "lucide-react";

interface ChatWindowProps {
  messages: Message[];
  user: User;
  onSendMessage: (content: string) => Promise<void>;
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

export default function ChatWindow({
  messages,
  user,
  onSendMessage,
  onToggleSidebar,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setInput("");
    setIsLoading(true);
    try {
      await onSendMessage(trimmed);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

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
        <div className="w-8 h-8 bg-santoni-600 rounded-lg flex items-center justify-center">
          <span className="text-white text-sm font-bold">S</span>
        </div>
        <div>
          <h1 className="text-sm font-semibold text-gray-900">SantoniBot</h1>
          <p className="text-xs text-gray-500">
            Asistente inteligente de Alimentos Santoni
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-santoni-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <span className="text-santoni-600 text-3xl font-bold">S</span>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Bienvenido a SantoniBot
              </h2>
              <p className="text-gray-500 mb-6">
                Haz una consulta sobre cualquiera de las áreas disponibles:
                Finanzas, Contabilidad, Ventas, RRHH, Producción o Compras.
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {[
                  "¿Cuáles son los top 20 clientes por ventas?",
                  "¿Cuánto es la compra de arroz paddy en 2025?",
                  "Muéstrame el flujo de caja del mes",
                  "¿Cuántos empleados hay por departamento?",
                ].map((suggestion) => (
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
              msg.agent_used ? AGENT_LABELS[msg.agent_used] || msg.agent_used : undefined
            }
          />
        ))}

        {isLoading && (
          <div className="flex gap-3 message-animate">
            <div className="w-8 h-8 bg-santoni-600 rounded-full flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-bold">S</span>
            </div>
            <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
                <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white p-4">
        <form onSubmit={handleSubmit} className="flex items-end gap-2 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu consulta..."
              rows={1}
              className="input-field resize-none pr-4 max-h-32"
              style={{ minHeight: "44px" }}
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn-primary p-3 rounded-xl"
          >
            <Send size={18} />
          </button>
        </form>
        <p className="text-xs text-gray-400 text-center mt-2">
          SantoniBot puede cometer errores. Verifica la información importante.
        </p>
      </div>
    </div>
  );
}
