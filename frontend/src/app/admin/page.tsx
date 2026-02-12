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
  ShieldCheck,
  KeyRound,
  QrCode,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  Unlock,
  Palette,
  Upload,
  Image,
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
  const [tab, setTab] = useState<"stats" | "users" | "logs" | "security" | "appearance">("stats");
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
            { id: "security" as const, label: "Seguridad", icon: ShieldCheck },
            { id: "appearance" as const, label: "Apariencia", icon: Palette },
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

        {/* Security Tab */}
        {tab === "security" && (
          <SecurityPanel user={user} />
        )}

        {/* Appearance Tab */}
        {tab === "appearance" && <AppearancePanel />}

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

function SecurityPanel({ user }: { user: User }) {
  const [totpSetup, setTotpSetup] = useState<{
    secret: string;
    qr_uri: string;
  } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [totpMessage, setTotpMessage] = useState("");
  const [totpError, setTotpError] = useState("");
  const [totpEnabled, setTotpEnabled] = useState(user.totp_enabled);
  const [loadingTotp, setLoadingTotp] = useState(false);

  // Password change
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwMessage, setPwMessage] = useState("");
  const [pwError, setPwError] = useState("");
  const [loadingPw, setLoadingPw] = useState(false);

  // Security overview & locked users (IT management)
  const [secOverview, setSecOverview] = useState<{
    failed_logins_24h: number;
    account_lockouts_7d: number;
    currently_locked: number;
    totp_enabled_users: number;
    total_active_users: number;
    totp_coverage_pct: number;
    suspicious_ips: Array<{ ip: string; failed_attempts: number }>;
  } | null>(null);
  const [lockedUsers, setLockedUsers] = useState<
    Array<{
      id: number;
      username: string;
      full_name: string;
      department: string;
      failed_attempts: number;
      remaining_minutes: number;
    }>
  >([]);

  useEffect(() => {
    loadSecurityData();
  }, []);

  const loadSecurityData = async () => {
    try {
      const [overview, locked] = await Promise.all([
        api.getSecurityOverview(),
        api.getLockedUsers(),
      ]);
      setSecOverview(overview);
      setLockedUsers(locked);
    } catch {
      // ignore if not admin
    }
  };

  const handleUnlock = async (userId: number) => {
    try {
      await api.unlockUser(userId);
      loadSecurityData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al desbloquear");
    }
  };

  const handleSetupTotp = async () => {
    setTotpError("");
    setTotpMessage("");
    setLoadingTotp(true);
    try {
      const data = await api.totpSetup();
      setTotpSetup(data);
    } catch (err) {
      setTotpError(
        err instanceof Error ? err.message : "Error al configurar 2FA"
      );
    } finally {
      setLoadingTotp(false);
    }
  };

  const handleEnableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError("");
    setLoadingTotp(true);
    try {
      const res = await api.totpEnable(totpCode);
      setTotpMessage(res.message);
      setTotpEnabled(true);
      setTotpSetup(null);
      setTotpCode("");
    } catch (err) {
      setTotpError(
        err instanceof Error ? err.message : "Código incorrecto"
      );
    } finally {
      setLoadingTotp(false);
    }
  };

  const handleDisableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError("");
    setLoadingTotp(true);
    try {
      const res = await api.totpDisable(disableCode);
      setTotpMessage(res.message);
      setTotpEnabled(false);
      setDisableCode("");
    } catch (err) {
      setTotpError(
        err instanceof Error ? err.message : "Código incorrecto"
      );
    } finally {
      setLoadingTotp(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError("");
    setPwMessage("");

    if (newPw !== confirmPw) {
      setPwError("Las contraseñas no coinciden");
      return;
    }

    setLoadingPw(true);
    try {
      const res = await api.changePassword(currentPw, newPw);
      setPwMessage(res.message);
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      setPwError(
        err instanceof Error ? err.message : "Error al cambiar contraseña"
      );
    } finally {
      setLoadingPw(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Security Overview (IT Dashboard) */}
      {secOverview && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Shield size={20} className="text-santoni-600" />
            <h3 className="text-lg font-semibold">
              Panel de Seguridad (TI)
            </h3>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-600">
                {secOverview.failed_logins_24h}
              </div>
              <div className="text-xs text-red-500">
                Logins fallidos (24h)
              </div>
            </div>
            <div className="bg-orange-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-orange-600">
                {secOverview.account_lockouts_7d}
              </div>
              <div className="text-xs text-orange-500">
                Bloqueos (7 dias)
              </div>
            </div>
            <div className={`rounded-lg p-3 text-center ${secOverview.currently_locked > 0 ? "bg-red-50" : "bg-green-50"}`}>
              <div className={`text-2xl font-bold ${secOverview.currently_locked > 0 ? "text-red-600" : "text-green-600"}`}>
                {secOverview.currently_locked}
              </div>
              <div className={`text-xs ${secOverview.currently_locked > 0 ? "text-red-500" : "text-green-500"}`}>
                Cuentas bloqueadas
              </div>
            </div>
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {secOverview.totp_coverage_pct}%
              </div>
              <div className="text-xs text-blue-500">
                Usuarios con 2FA ({secOverview.totp_enabled_users}/{secOverview.total_active_users})
              </div>
            </div>
          </div>

          {secOverview.suspicious_ips.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <AlertTriangle size={14} className="text-orange-500" />
                IPs sospechosas (ultimos 7 dias)
              </h4>
              <div className="flex flex-wrap gap-2">
                {secOverview.suspicious_ips.map((item) => (
                  <span
                    key={item.ip}
                    className="inline-flex items-center gap-1 bg-red-50 text-red-700 text-xs px-2 py-1 rounded font-mono"
                  >
                    {item.ip}
                    <span className="bg-red-200 text-red-800 px-1 rounded">
                      {item.failed_attempts}x
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Locked Users Management */}
      {lockedUsers.length > 0 && (
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Lock size={20} className="text-red-500" />
            <h3 className="text-lg font-semibold text-red-700">
              Cuentas Bloqueadas ({lockedUsers.length})
            </h3>
          </div>
          <div className="space-y-2">
            {lockedUsers.map((lu) => (
              <div
                key={lu.id}
                className="flex items-center justify-between bg-red-50 rounded-lg px-4 py-3"
              >
                <div>
                  <span className="font-medium text-gray-900">
                    {lu.full_name}
                  </span>
                  <span className="text-gray-500 text-sm ml-2">
                    @{lu.username}
                  </span>
                  <span className="text-red-500 text-xs ml-2">
                    ({lu.failed_attempts} intentos, {lu.remaining_minutes} min restantes)
                  </span>
                </div>
                <button
                  onClick={() => handleUnlock(lu.id)}
                  className="flex items-center gap-1 bg-white border border-gray-200 text-gray-700 px-3 py-1.5 rounded-lg text-sm hover:bg-green-50 hover:border-green-300 hover:text-green-700 transition-colors"
                >
                  <Unlock size={14} />
                  Desbloquear
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2FA Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <ShieldCheck size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">
            Autenticación de Dos Factores (2FA)
          </h3>
          {totpEnabled ? (
            <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              <CheckCircle2 size={12} /> Activo
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
              <XCircle size={12} /> Inactivo
            </span>
          )}
        </div>

        <p className="text-sm text-gray-500 mb-4">
          Agrega una capa extra de seguridad a tu cuenta usando Google
          Authenticator u otra aplicación compatible con TOTP.
        </p>

        {totpMessage && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm p-3 rounded-lg mb-4">
            {totpMessage}
          </div>
        )}
        {totpError && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
            {totpError}
          </div>
        )}

        {!totpEnabled && !totpSetup && (
          <button
            onClick={handleSetupTotp}
            disabled={loadingTotp}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <QrCode size={16} />
            {loadingTotp ? "Generando..." : "Configurar 2FA"}
          </button>
        )}

        {!totpEnabled && totpSetup && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-2">
                1. Escanea este código QR con Google Authenticator:
              </p>
              <div className="flex justify-center my-4">
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  {/* QR code rendered as URI - user scans with their app */}
                  <div className="text-center">
                    <QrCode size={120} className="text-gray-800 mx-auto" />
                    <p className="text-xs text-gray-500 mt-2 break-all max-w-xs">
                      {totpSetup.qr_uri}
                    </p>
                  </div>
                </div>
              </div>
              <p className="text-sm font-medium text-gray-700 mb-1">
                2. O ingresa este código manualmente:
              </p>
              <code className="block bg-white border border-gray-200 rounded px-3 py-2 text-center font-mono text-lg tracking-wider select-all">
                {totpSetup.secret}
              </code>
            </div>

            <form onSubmit={handleEnableTotp} className="flex items-end gap-3">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  3. Ingresa el código de 6 dígitos para verificar:
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) =>
                    setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  className="input-field text-center text-xl tracking-[0.4em] font-mono"
                  placeholder="000000"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loadingTotp || totpCode.length !== 6}
                className="btn-primary text-sm whitespace-nowrap"
              >
                {loadingTotp ? "Verificando..." : "Activar 2FA"}
              </button>
            </form>
          </div>
        )}

        {totpEnabled && (
          <form onSubmit={handleDisableTotp} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Para desactivar 2FA, ingresa tu código actual:
              </label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={disableCode}
                onChange={(e) =>
                  setDisableCode(
                    e.target.value.replace(/\D/g, "").slice(0, 6)
                  )
                }
                className="input-field text-center text-xl tracking-[0.4em] font-mono"
                placeholder="000000"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loadingTotp || disableCode.length !== 6}
              className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-600 transition-colors whitespace-nowrap"
            >
              Desactivar 2FA
            </button>
          </form>
        )}
      </div>

      {/* Avatar Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Image size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">Foto de Perfil</h3>
        </div>
        <div className="flex items-center gap-6">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt="Avatar"
              className="w-20 h-20 rounded-full object-cover border-2 border-gray-200"
            />
          ) : (
            <div className="w-20 h-20 bg-santoni-100 rounded-full flex items-center justify-center text-2xl font-bold text-santoni-600">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="space-y-2">
            <label className="cursor-pointer inline-flex items-center gap-2 btn-primary text-sm">
              <Upload size={14} />
              Cambiar foto
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  try {
                    await api.uploadAvatar(file);
                    window.location.reload();
                  } catch (err) {
                    alert(
                      err instanceof Error
                        ? err.message
                        : "Error al subir foto"
                    );
                  }
                }}
              />
            </label>
            {user.avatar_url && (
              <button
                onClick={async () => {
                  try {
                    await api.deleteAvatar();
                    window.location.reload();
                  } catch {
                    // ignore
                  }
                }}
                className="block text-xs text-red-500 hover:text-red-700"
              >
                Eliminar foto
              </button>
            )}
            <p className="text-xs text-gray-400">
              JPG, PNG o WebP (max 5MB)
            </p>
          </div>
        </div>
      </div>

      {/* Password Change Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <KeyRound size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">Cambiar Contraseña</h3>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          La contraseña debe tener mínimo 8 caracteres, una mayúscula, una
          minúscula, un número y un carácter especial (!@#$%^&*).
        </p>

        {pwMessage && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm p-3 rounded-lg mb-4">
            {pwMessage}
          </div>
        )}
        {pwError && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
            {pwError}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-3 max-w-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña actual
            </label>
            <input
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nueva contraseña
            </label>
            <input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              className="input-field"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar nueva contraseña
            </label>
            <input
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              className="input-field"
              required
              minLength={8}
            />
          </div>
          <button
            type="submit"
            disabled={loadingPw || !currentPw || !newPw || !confirmPw}
            className="btn-primary text-sm"
          >
            {loadingPw ? "Actualizando..." : "Cambiar Contraseña"}
          </button>
        </form>
      </div>
    </div>
  );
}

function AppearancePanel() {
  const [branding, setBranding] = useState({
    company_name: "SantoniBot",
    company_subtitle: "Sistema Inteligente de Análisis",
    primary_color: "#e86c25",
    logo_url: "",
    login_logo_url: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.getBranding().then(setBranding).catch(() => {});
  }, []);

  const handleSaveText = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await api.updateBranding({
        company_name: branding.company_name,
        company_subtitle: branding.company_subtitle,
        primary_color: branding.primary_color,
      });
      setMessage("Configuración guardada exitosamente");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    type: "logo" | "login"
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const result =
        type === "logo"
          ? await api.uploadLogo(file)
          : await api.uploadLoginLogo(file);
      setBranding((prev) => ({
        ...prev,
        [type === "logo" ? "logo_url" : "login_logo_url"]: result.url,
      }));
      setMessage("Logo actualizado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al subir");
    }
  };

  return (
    <div className="space-y-6">
      {/* Text settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Palette size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">Personalización de la Plataforma</h3>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          Configura el nombre, logo y colores de la plataforma.
          Los cambios se aplican a todos los usuarios al recargar.
        </p>

        {message && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm p-3 rounded-lg mb-4">
            {message}
          </div>
        )}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSaveText} className="space-y-4 max-w-lg">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nombre de la plataforma
            </label>
            <input
              type="text"
              value={branding.company_name}
              onChange={(e) =>
                setBranding((p) => ({ ...p, company_name: e.target.value }))
              }
              className="input-field"
              maxLength={50}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Subtítulo
            </label>
            <input
              type="text"
              value={branding.company_subtitle}
              onChange={(e) =>
                setBranding((p) => ({
                  ...p,
                  company_subtitle: e.target.value,
                }))
              }
              className="input-field"
              maxLength={100}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Color primario
            </label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={branding.primary_color}
                onChange={(e) =>
                  setBranding((p) => ({
                    ...p,
                    primary_color: e.target.value,
                  }))
                }
                className="w-10 h-10 rounded cursor-pointer border border-gray-200"
              />
              <input
                type="text"
                value={branding.primary_color}
                onChange={(e) =>
                  setBranding((p) => ({
                    ...p,
                    primary_color: e.target.value,
                  }))
                }
                className="input-field w-32 font-mono text-sm"
                maxLength={7}
              />
              <div
                className="w-20 h-10 rounded-lg"
                style={{ backgroundColor: branding.primary_color }}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="btn-primary text-sm"
          >
            {saving ? "Guardando..." : "Guardar cambios"}
          </button>
        </form>
      </div>

      {/* Logo uploads */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Image size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">Logos</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Main Logo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Logo principal (sidebar y header)
            </label>
            <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
              {branding.logo_url ? (
                <img
                  src={branding.logo_url}
                  alt="Logo"
                  className="max-h-16 mx-auto mb-2 object-contain"
                />
              ) : (
                <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Upload size={24} className="text-gray-400" />
                </div>
              )}
              <label className="cursor-pointer inline-flex items-center gap-1 text-sm text-santoni-600 hover:text-santoni-700 font-medium">
                <Upload size={14} />
                {branding.logo_url ? "Cambiar logo" : "Subir logo"}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  className="hidden"
                  onChange={(e) => handleLogoUpload(e, "logo")}
                />
              </label>
              <p className="text-xs text-gray-400 mt-1">
                PNG, JPG, WebP o SVG (max 5MB)
              </p>
            </div>
          </div>

          {/* Login Logo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Logo de la pagina de login
            </label>
            <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
              {branding.login_logo_url ? (
                <img
                  src={branding.login_logo_url}
                  alt="Login Logo"
                  className="max-h-16 mx-auto mb-2 object-contain"
                />
              ) : (
                <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Upload size={24} className="text-gray-400" />
                </div>
              )}
              <label className="cursor-pointer inline-flex items-center gap-1 text-sm text-santoni-600 hover:text-santoni-700 font-medium">
                <Upload size={14} />
                {branding.login_logo_url ? "Cambiar logo" : "Subir logo"}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  className="hidden"
                  onChange={(e) => handleLogoUpload(e, "login")}
                />
              </label>
              <p className="text-xs text-gray-400 mt-1">
                PNG, JPG, WebP o SVG (max 5MB)
              </p>
            </div>
          </div>
        </div>
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
