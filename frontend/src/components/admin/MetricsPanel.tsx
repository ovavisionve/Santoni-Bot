"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { DEPARTMENT_LABELS } from "./constants";

export default function MetricsPanel() {
  const [metrics, setMetrics] = useState<{
    period_days: number;
    daily_messages: Array<{ date: string; count: number }>;
    daily_conversations: Array<{ date: string; count: number }>;
    top_users: Array<{ username: string; full_name: string; department: string; message_count: number }>;
    department_breakdown: Array<{ department: string; active_users: number; messages: number }>;
    avg_messages_per_conversation: number;
  } | null>(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    loadMetrics();
  }, [days]);

  const loadMetrics = async () => {
    try {
      const data = await api.getUsageMetrics(days);
      setMetrics(data);
    } catch {
      // ignore
    }
  };

  if (!metrics) return <div className="text-gray-400 text-center py-8">Cargando métricas...</div>;

  const maxMsgCount = Math.max(...metrics.daily_messages.map(d => d.count), 1);

  return (
    <div className="space-y-6">
      {/* Period selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Periodo:</span>
        {[7, 14, 30].map(d => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              days === d ? "bg-santoni-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {d} dias
          </button>
        ))}
      </div>

      {/* Activity chart (simple bar chart) */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold mb-4">Mensajes diarios</h3>
        <div className="flex items-end gap-1 h-40">
          {metrics.daily_messages.map((day) => (
            <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-xs text-gray-400">{day.count}</span>
              <div
                className="w-full bg-santoni-500 rounded-t-sm min-h-[2px] transition-all"
                style={{ height: `${(day.count / maxMsgCount) * 100}%` }}
              />
              <span className="text-xs text-gray-400 truncate w-full text-center">
                {new Date(day.date).toLocaleDateString("es-VE", { day: "2-digit", month: "2-digit" })}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Promedio mensajes/conversacion</div>
          <div className="text-2xl font-bold text-gray-900">{metrics.avg_messages_per_conversation}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Conversaciones ({days}d)</div>
          <div className="text-2xl font-bold text-gray-900">
            {metrics.daily_conversations.reduce((s, d) => s + d.count, 0)}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500 mb-1">Mensajes ({days}d)</div>
          <div className="text-2xl font-bold text-gray-900">
            {metrics.daily_messages.reduce((s, d) => s + d.count, 0)}
          </div>
        </div>
      </div>

      {/* Top users */}
      {metrics.top_users.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold mb-4">Top usuarios ({days} dias)</h3>
          <div className="space-y-2">
            {metrics.top_users.map((u, i) => (
              <div key={u.username} className="flex items-center gap-3">
                <span className="text-sm font-bold text-gray-400 w-6">{i + 1}.</span>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">{u.full_name}</div>
                  <div className="text-xs text-gray-400">
                    @{u.username} &middot; {DEPARTMENT_LABELS[u.department] || u.department}
                  </div>
                </div>
                <span className="text-sm font-bold text-santoni-600">{u.message_count} msgs</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Department breakdown */}
      {metrics.department_breakdown.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold mb-4">Actividad por departamento</h3>
          <div className="space-y-3">
            {metrics.department_breakdown
              .sort((a, b) => b.messages - a.messages)
              .map((d) => {
                const maxDeptMsg = Math.max(...metrics.department_breakdown.map(x => x.messages), 1);
                return (
                  <div key={d.department} className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-36 truncate">
                      {DEPARTMENT_LABELS[d.department] || d.department || "Sin depto"}
                    </span>
                    <div className="flex-1 bg-gray-100 rounded-full h-5">
                      <div
                        className="bg-santoni-500 h-5 rounded-full flex items-center justify-end pr-2"
                        style={{ width: `${Math.max((d.messages / maxDeptMsg) * 100, 8)}%` }}
                      >
                        <span className="text-xs text-white font-medium">{d.messages}</span>
                      </div>
                    </div>
                    <span className="text-xs text-gray-400 w-20 text-right">{d.active_users} usuarios</span>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
