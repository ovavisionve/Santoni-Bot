"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import type { User, SystemStats } from "@/types";
import {
  Users,
  MessageSquare,
  BarChart3,
  Shield,
  ArrowLeft,
  Plus,
  Trash2,
  Edit,
} from "lucide-react";
import Link from "next/link";

const DEPARTMENT_LABELS: Record<string, string> = {
  finanzas: "Finanzas",
  contabilidad: "Contabilidad",
  ventas: "Ventas",
  rrhh: "RRHH",
  produccion: "Producción",
  compras_insumos: "Compras Insumos",
  compras_productores: "Compras Productores",
};

const ROLE_LABELS: Record<string, string> = {
  usuario: "Usuario",
  supervisor: "Supervisor",
  administrador: "Administrador",
};

export default function AdminPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [tab, setTab] = useState<"stats" | "users" | "logs">("stats");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUser, setNewUser] = useState({
    email: "",
    username: "",
    full_name: "",
    password: "",
    role: "usuario",
    department: "ventas",
  });
  const [auditLogs, setAuditLogs] = useState<
    Array<{
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
    }>
  >([]);

  useEffect(() => {
    if (!loading && (!user || user.role !== "administrador")) {
      router.push("/chat");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (user?.role === "administrador") {
      loadData();
    }
  }, [user, tab]);

  const loadData = async () => {
    try {
      if (tab === "stats") {
        const s = await api.getStats();
        setStats(s);
      } else if (tab === "users") {
        const u = await api.getUsers();
        setUsers(u);
      } else if (tab === "logs") {
        const l = await api.getAuditLogs();
        setAuditLogs(l.data);
      }
    } catch {
      // ignore
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createUser(newUser);
      setShowCreateUser(false);
      setNewUser({
        email: "",
        username: "",
        full_name: "",
        password: "",
        role: "usuario",
        department: "ventas",
      });
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al crear usuario");
    }
  };

  const handleDeleteUser = async (id: number) => {
    if (!confirm("¿Estás seguro de eliminar este usuario?")) return;
    try {
      await api.deleteUser(id);
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al eliminar");
    }
  };

  if (loading || !user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            href="/chat"
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ArrowLeft size={20} />
          </Link>
          <div className="w-8 h-8 bg-santoni-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">S</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold">
              Panel de Administración
            </h1>
            <p className="text-xs text-gray-500">SantoniBot</p>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto p-6">
        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 mb-6 w-fit">
          {[
            { id: "stats" as const, label: "Estadísticas", icon: BarChart3 },
            { id: "users" as const, label: "Usuarios", icon: Users },
            { id: "logs" as const, label: "Auditoría", icon: Shield },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === id
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {/* Stats Tab */}
        {tab === "stats" && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label="Usuarios Activos"
                value={stats.users.active}
                total={stats.users.total}
                icon={Users}
              />
              <StatCard
                label="Conversaciones"
                value={stats.conversations}
                icon={MessageSquare}
              />
              <StatCard
                label="Mensajes Totales"
                value={stats.messages}
                icon={BarChart3}
              />
              <StatCard
                label="Agentes Activos"
                value={Object.keys(stats.agent_usage).length}
                total={7}
                icon={Shield}
              />
            </div>

            {Object.keys(stats.agent_usage).length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-semibold mb-4">Uso por Agente</h3>
                <div className="space-y-3">
                  {Object.entries(stats.agent_usage)
                    .sort(([, a], [, b]) => b - a)
                    .map(([agent, count]) => (
                      <div key={agent} className="flex items-center gap-3">
                        <span className="text-sm text-gray-600 w-40">
                          {DEPARTMENT_LABELS[agent] || agent}
                        </span>
                        <div className="flex-1 bg-gray-100 rounded-full h-6">
                          <div
                            className="bg-santoni-500 h-6 rounded-full flex items-center justify-end pr-2"
                            style={{
                              width: `${Math.max(
                                (count /
                                  Math.max(
                                    ...Object.values(stats.agent_usage)
                                  )) *
                                  100,
                                10
                              )}%`,
                            }}
                          >
                            <span className="text-xs text-white font-medium">
                              {count}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Users Tab */}
        {tab === "users" && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold">
                Usuarios ({users.length})
              </h2>
              <button
                onClick={() => setShowCreateUser(!showCreateUser)}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                <Plus size={16} />
                Nuevo Usuario
              </button>
            </div>

            {showCreateUser && (
              <form
                onSubmit={handleCreateUser}
                className="bg-white rounded-xl border border-gray-200 p-6 space-y-4"
              >
                <h3 className="font-semibold">Crear Usuario</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input
                    className="input-field"
                    placeholder="Nombre completo"
                    value={newUser.full_name}
                    onChange={(e) =>
                      setNewUser({ ...newUser, full_name: e.target.value })
                    }
                    required
                  />
                  <input
                    className="input-field"
                    placeholder="Username"
                    value={newUser.username}
                    onChange={(e) =>
                      setNewUser({ ...newUser, username: e.target.value })
                    }
                    required
                  />
                  <input
                    className="input-field"
                    type="email"
                    placeholder="Email"
                    value={newUser.email}
                    onChange={(e) =>
                      setNewUser({ ...newUser, email: e.target.value })
                    }
                    required
                  />
                  <input
                    className="input-field"
                    type="password"
                    placeholder="Contraseña"
                    value={newUser.password}
                    onChange={(e) =>
                      setNewUser({ ...newUser, password: e.target.value })
                    }
                    required
                  />
                  <select
                    className="input-field"
                    value={newUser.role}
                    onChange={(e) =>
                      setNewUser({ ...newUser, role: e.target.value })
                    }
                  >
                    <option value="usuario">Usuario</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="administrador">Administrador</option>
                  </select>
                  <select
                    className="input-field"
                    value={newUser.department}
                    onChange={(e) =>
                      setNewUser({ ...newUser, department: e.target.value })
                    }
                  >
                    {Object.entries(DEPARTMENT_LABELS).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2">
                  <button type="submit" className="btn-primary text-sm">
                    Crear
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateUser(false)}
                    className="btn-secondary text-sm"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Nombre
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Usuario
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Departamento
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Rol
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Estado
                    </th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">{u.full_name}</td>
                      <td className="px-4 py-3 text-gray-500">{u.username}</td>
                      <td className="px-4 py-3">
                        {DEPARTMENT_LABELS[u.department] || u.department}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            u.role === "administrador"
                              ? "bg-purple-100 text-purple-700"
                              : u.role === "supervisor"
                                ? "bg-blue-100 text-blue-700"
                                : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {ROLE_LABELS[u.role] || u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block w-2 h-2 rounded-full ${
                            u.is_active ? "bg-green-500" : "bg-gray-300"
                          }`}
                        />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Audit Logs Tab */}
        {tab === "logs" && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Fecha
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Usuario
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Acción
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Detalle
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    Agente
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">
                    IP
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {auditLogs.map((log) => (
                  <tr
                    key={log.id}
                    className={`hover:bg-gray-50 ${
                      log.action === "access_denied" || log.action === "login_failed"
                        ? "bg-red-50"
                        : ""
                    }`}
                  >
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                      {new Date(log.created_at).toLocaleString("es-VE")}
                    </td>
                    <td className="px-4 py-3">
                      {log.username ? (
                        <div>
                          <div className="font-medium text-gray-900 text-xs">
                            {log.full_name}
                          </div>
                          <div className="text-gray-400 text-xs">
                            @{log.username}
                          </div>
                        </div>
                      ) : (
                        <span className="text-gray-400 text-xs italic">
                          Desconocido
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          log.action === "login"
                            ? "bg-green-100 text-green-700"
                            : log.action === "login_failed"
                              ? "bg-red-100 text-red-700"
                              : log.action === "access_denied"
                                ? "bg-red-100 text-red-700"
                                : log.action === "chat_query"
                                  ? "bg-blue-100 text-blue-700"
                                  : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {log.action === "login"
                          ? "Inicio sesión"
                          : log.action === "login_failed"
                            ? "Login fallido"
                            : log.action === "access_denied"
                              ? "ACCESO DENEGADO"
                              : log.action === "chat_query"
                                ? "Consulta"
                                : log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 max-w-sm truncate text-xs">
                      {log.detail}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {log.agent_used
                        ? DEPARTMENT_LABELS[log.agent_used] || log.agent_used
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs font-mono">
                      {log.ip_address || "-"}
                    </td>
                  </tr>
                ))}
                {auditLogs.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-gray-400"
                    >
                      No hay registros de auditoría
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  total,
  icon: Icon,
}: {
  label: string;
  value: number;
  total?: number;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">{label}</span>
        <Icon size={18} className="text-santoni-500" />
      </div>
      <div className="text-2xl font-bold text-gray-900">
        {value}
        {total !== undefined && (
          <span className="text-sm font-normal text-gray-400">
            {" "}
            / {total}
          </span>
        )}
      </div>
    </div>
  );
}
