"use client";

import type { Message } from "@/types";
import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  message: Message;
  userName: string;
  agentLabel?: string;
}

export default function ChatMessage({
  message,
  userName,
  agentLabel,
}: ChatMessageProps) {
  const isUser = message.role === "user";

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
          } prose prose-sm max-w-none ${
            isUser ? "prose-invert" : ""
          }`}
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

        {/* Timestamp */}
        <div
          className={`text-xs mt-1 ${
            isUser ? "text-santoni-200" : "text-gray-400"
          }`}
        >
          {new Date(message.created_at).toLocaleTimeString("es-VE", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}
