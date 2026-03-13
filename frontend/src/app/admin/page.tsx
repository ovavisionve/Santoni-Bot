"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import type { User, SystemStats, Organization } from "@/types";
import {
  Users,
  MessageSquare,
  BarChart3,
  Shield,
  ArrowLeft,
  TrendingUp,
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
  Download,
  ChevronDown,
  ChevronUp,
  Eye,
  Search,
  Filter,
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
  vendedor: "Vendedor",
};

export default function AdminPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [tab, setTab] = useState<"stats" | "users" | "logs" | "security" | "metrics">("stats");
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
    extra_departments: "" as string,
    allowed_org_ids: "" as string,
    idempiere_salesrep_id: null as number | null,
    sensitivity_level: 0,
  });
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editForm, setEditForm] = useState({
    admin_password: "",
    email: "",
    full_name: "",
    role: "",
    department: "",
    extra_departments: "",
    allowed_org_ids: "",
    idempiere_salesrep_id: null as number | null,
    sensitivity_level: 0,
    is_active: true,
    new_password: "",
  });
  const [editError, setEditError] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [salesreps, setSalesreps] = useState<{ id: number; name: string }[]>([]);
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
        const [u, orgs, reps] = await Promise.all([
          api.getUsers(),
          api.getOrganizations().catch(() => [] as Organization[]),
          api.getSalesreps().catch(() => [] as { id: number; name: string }[]),
        ]);
        setUsers(u);
        setOrganizations(orgs);
        setSalesreps(reps);
      } else if (tab === "logs") {
        const [l, u] = await Promise.all([
          api.getAuditLogs(),
          users.length ? Promise.resolve(users) : api.getUsers(),
        ]);
        setAuditLogs(l.data);
        if (!users.length) setUsers(u);
      }
    } catch {
      // ignore
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...newUser,
        extra_departments: newUser.extra_departments || null,
        allowed_org_ids: newUser.allowed_org_ids || null,
        idempiere_salesrep_id: newUser.idempiere_salesrep_id || null,
      };
      await api.createUser(payload);
      setShowCreateUser(false);
      setNewUser({
        email: "",
        username: "",
        full_name: "",
        password: "",
        role: "usuario",
        department: "ventas",
        extra_departments: "",
        allowed_org_ids: "",
        idempiere_salesrep_id: null,
        sensitivity_level: 0,
      });
      loadData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al crear usuario");
    }
  };

  const openEditModal = (u: User) => {
    setEditingUser(u);
    setEditForm({
      admin_password: "",
      email: u.email,
      full_name: u.full_name,
      role: u.role,
      department: u.department,
      extra_departments: u.extra_departments || "",
      allowed_org_ids: u.allowed_org_ids || "",
      idempiere_salesrep_id: u.idempiere_salesrep_id,
      sensitivity_level: u.sensitivity_level ?? 0,
      is_active: u.is_active,
      new_password: "",
    });
    setEditError("");
  };

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setEditLoading(true);
    setEditError("");
    try {
      await api.updateUser(editingUser.id, {
        admin_password: editForm.admin_password,
        email: editForm.email,
        full_name: editForm.full_name,
        role: editForm.role,
        department: editForm.role === "vendedor" ? "ventas" : editForm.department,
        extra_departments: editForm.extra_departments || null,
        allowed_org_ids: editForm.allowed_org_ids || null,
        idempiere_salesrep_id: editForm.idempiere_salesrep_id,
        sensitivity_level: editForm.sensitivity_level,
        is_active: editForm.is_active,
        new_password: editForm.new_password || null,
      });
      setEditingUser(null);
      loadData();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Error al actualizar usuario");
    } finally {
      setEditLoading(false);
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
          <img src="/santoni-logo.png" alt="Santoni" className="h-8 w-auto" />
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
            { id: "metrics" as const, label: "Métricas", icon: TrendingUp },
            { id: "security" as const, label: "Seguridad", icon: ShieldCheck },
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
                    onChange={(e) => {
                      const role = e.target.value;
                      const updates: Partial<typeof newUser> = { role, extra_departments: "" };
                      if (role === "vendedor") {
                        updates.department = "ventas";
                      } else if (role === "administrador") {
                        updates.department = "finanzas";
                      }
                      if (role !== "vendedor") {
                        updates.idempiere_salesrep_id = null;
                      }
                      setNewUser({ ...newUser, ...updates });
                    }}
                  >
                    {Object.entries(ROLE_LABELS).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                  {/* Vendedor: fixed to Ventas, Administrador: all depts */}
                  {newUser.role === "vendedor" ? (
                    <div className="input-field bg-gray-50 text-gray-500 flex items-center">
                      Ventas (fijo para vendedores)
                    </div>
                  ) : newUser.role === "administrador" ? (
                    <div className="input-field bg-gray-50 text-gray-500 flex items-center">
                      Todas las áreas
                    </div>
                  ) : (
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
                  )}
                </div>
                {/* Supervisor: additional departments checkboxes */}
                {newUser.role === "supervisor" && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Departamentos adicionales
                    </label>
                    <p className="text-xs text-gray-400">
                      El supervisor ya tiene acceso a su departamento principal. Selecciona áreas adicionales si corresponde.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 border border-gray-200 rounded-lg p-3">
                      {Object.entries(DEPARTMENT_LABELS)
                        .filter(([key]) => key !== newUser.department)
                        .map(([key, label]) => {
                          const extras = newUser.extra_departments
                            .split(",")
                            .filter(Boolean);
                          const selected = extras.includes(key);
                          return (
                            <label
                              key={key}
                              className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${
                                selected
                                  ? "bg-santoni-50 border border-santoni-200"
                                  : "hover:bg-gray-50"
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={selected}
                                onChange={() => {
                                  const next = selected
                                    ? extras.filter((x) => x !== key)
                                    : [...extras, key];
                                  setNewUser({
                                    ...newUser,
                                    extra_departments: next.join(","),
                                  });
                                }}
                                className="rounded border-gray-300 text-santoni-600 focus:ring-santoni-500"
                              />
                              <span className="text-gray-700">{label}</span>
                            </label>
                          );
                        })}
                    </div>
                  </div>
                )}
                {organizations.length > 0 && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Empresas / Organizaciones (iDempiere)
                    </label>
                    <p className="text-xs text-gray-400">
                      Sin selección = acceso a todas las empresas
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3">
                      {organizations.map((org) => {
                        const selected = newUser.allowed_org_ids
                          .split(",")
                          .filter(Boolean)
                          .includes(String(org.id));
                        return (
                          <label
                            key={org.id}
                            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${
                              selected
                                ? "bg-santoni-50 border border-santoni-200"
                                : "hover:bg-gray-50"
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={() => {
                                const ids = newUser.allowed_org_ids
                                  .split(",")
                                  .filter(Boolean);
                                const idStr = String(org.id);
                                const next = selected
                                  ? ids.filter((x) => x !== idStr)
                                  : [...ids, idStr];
                                setNewUser({
                                  ...newUser,
                                  allowed_org_ids: next.join(","),
                                });
                              }}
                              className="rounded border-gray-300 text-santoni-600 focus:ring-santoni-500"
                            />
                            <span className="text-gray-700">{org.name}</span>
                            <span className="text-gray-400 text-xs">
                              ({org.value})
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                )}
                {newUser.role === "vendedor" && salesreps.length > 0 && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Vendedor en iDempiere
                    </label>
                    <p className="text-xs text-gray-400">
                      Selecciona el vendedor de iDempiere que corresponde a este usuario. Solo verá SUS ventas.
                    </p>
                    <select
                      value={newUser.idempiere_salesrep_id ?? ""}
                      onChange={(e) =>
                        setNewUser({
                          ...newUser,
                          idempiere_salesrep_id: e.target.value
                            ? Number(e.target.value)
                            : null,
                        })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-santoni-500 focus:border-santoni-500"
                    >
                      <option value="">-- Seleccionar vendedor --</option>
                      {salesreps.map((rep) => (
                        <option key={rep.id} value={rep.id}>
                          {rep.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {/* Sensitivity level selector */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Nivel de acceso a datos
                  </label>
                  <div className="space-y-2">
                    {[
                      { value: 0, label: "Basico", desc: "Datos operativos (ventas, produccion, compras)", color: "bg-green-100 text-green-800 border-green-300" },
                      { value: 1, label: "Financiero", desc: "Datos contables y financieros", color: "bg-blue-100 text-blue-800 border-blue-300" },
                      { value: 2, label: "Confidencial", desc: "Nomina, salarios, datos personales (RRHH)", color: "bg-red-100 text-red-800 border-red-300" },
                    ].map((level) => (
                      <label
                        key={level.value}
                        className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                          newUser.sensitivity_level === level.value
                            ? level.color
                            : "bg-white border-gray-200 hover:bg-gray-50"
                        }`}
                      >
                        <input
                          type="radio"
                          name="sensitivity_level"
                          value={level.value}
                          checked={newUser.sensitivity_level === level.value}
                          onChange={() =>
                            setNewUser({ ...newUser, sensitivity_level: level.value })
                          }
                          className="text-santoni-600 focus:ring-santoni-500"
                        />
                        <div>
                          <div className="text-sm font-medium">{level.label}</div>
                          <div className="text-xs opacity-70">{level.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
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
                      Sensibilidad
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">
                      Empresas
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
                        <div>
                          {u.role === "administrador"
                            ? "Todas las áreas"
                            : DEPARTMENT_LABELS[u.department] || u.department}
                          {u.extra_departments && (
                            <div className="text-xs text-gray-400 mt-0.5">
                              + {u.extra_departments.split(",").map(d => DEPARTMENT_LABELS[d.trim()] || d.trim()).join(", ")}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                            u.role === "administrador"
                              ? "bg-purple-100 text-purple-700"
                              : u.role === "supervisor"
                                ? "bg-blue-100 text-blue-700"
                                : u.role === "vendedor"
                                  ? "bg-green-100 text-green-700"
                                  : "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {ROLE_LABELS[u.role] || u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          (u.sensitivity_level ?? 0) === 2
                            ? "bg-red-100 text-red-700"
                            : (u.sensitivity_level ?? 0) === 1
                              ? "bg-blue-100 text-blue-700"
                              : "bg-green-100 text-green-700"
                        }`}>
                          {(u.sensitivity_level ?? 0) === 2 ? "Confidencial" : (u.sensitivity_level ?? 0) === 1 ? "Financiero" : "Basico"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {u.allowed_org_ids
                          ? u.allowed_org_ids
                              .split(",")
                              .map((id) => {
                                const org = organizations.find(
                                  (o) => String(o.id) === id.trim()
                                );
                                return org ? org.name : id.trim();
                              })
                              .join(", ")
                          : "Todas"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block w-2 h-2 rounded-full ${
                            u.is_active ? "bg-green-500" : "bg-gray-300"
                          }`}
                        />
                      </td>
                      <td className="px-4 py-3 text-right flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(u)}
                          className="text-gray-400 hover:text-santoni-600 transition-colors"
                          title="Editar usuario"
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                          title="Eliminar usuario"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Edit User Modal */}
            {editingUser && (
              <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                  <form onSubmit={handleEditUser} className="p-6 space-y-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-semibold">
                        Editar: {editingUser.full_name}
                      </h3>
                      <button
                        type="button"
                        onClick={() => setEditingUser(null)}
                        className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                      >
                        &times;
                      </button>
                    </div>

                    {editError && (
                      <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg">
                        {editError}
                      </div>
                    )}

                    {/* Admin password - required to confirm */}
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <label className="block text-sm font-medium text-amber-800 mb-1">
                        <Lock size={14} className="inline mr-1" />
                        Confirma tu contraseña de administrador
                      </label>
                      <input
                        type="password"
                        value={editForm.admin_password}
                        onChange={(e) => setEditForm({ ...editForm, admin_password: e.target.value })}
                        className="input-field"
                        placeholder="Tu contraseña actual"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
                        <input
                          className="input-field"
                          value={editForm.full_name}
                          onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                        <input
                          className="input-field"
                          type="email"
                          value={editForm.email}
                          onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Rol</label>
                        <select
                          className="input-field"
                          value={editForm.role}
                          onChange={(e) => {
                            const role = e.target.value;
                            const updates: Partial<typeof editForm> = { role, extra_departments: "" };
                            if (role === "vendedor") updates.department = "ventas";
                            else if (role === "administrador") updates.department = "finanzas";
                            if (role !== "vendedor") updates.idempiere_salesrep_id = null;
                            setEditForm({ ...editForm, ...updates });
                          }}
                        >
                          {Object.entries(ROLE_LABELS).map(([key, label]) => (
                            <option key={key} value={key}>{label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Departamento principal</label>
                        {editForm.role === "vendedor" ? (
                          <div className="input-field bg-gray-50 text-gray-500 flex items-center">Ventas (fijo)</div>
                        ) : editForm.role === "administrador" ? (
                          <div className="input-field bg-gray-50 text-gray-500 flex items-center">Todas las areas</div>
                        ) : (
                          <select
                            className="input-field"
                            value={editForm.department}
                            onChange={(e) => setEditForm({ ...editForm, department: e.target.value })}
                          >
                            {Object.entries(DEPARTMENT_LABELS).map(([key, label]) => (
                              <option key={key} value={key}>{label}</option>
                            ))}
                          </select>
                        )}
                      </div>
                    </div>

                    {/* Extra departments for supervisor */}
                    {editForm.role === "supervisor" && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700">Departamentos adicionales</label>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 border border-gray-200 rounded-lg p-3">
                          {Object.entries(DEPARTMENT_LABELS)
                            .filter(([key]) => key !== editForm.department)
                            .map(([key, label]) => {
                              const extras = editForm.extra_departments.split(",").filter(Boolean);
                              const selected = extras.includes(key);
                              return (
                                <label key={key} className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${selected ? "bg-santoni-50 border border-santoni-200" : "hover:bg-gray-50"}`}>
                                  <input
                                    type="checkbox"
                                    checked={selected}
                                    onChange={() => {
                                      const next = selected ? extras.filter((x) => x !== key) : [...extras, key];
                                      setEditForm({ ...editForm, extra_departments: next.join(",") });
                                    }}
                                    className="rounded border-gray-300 text-santoni-600 focus:ring-santoni-500"
                                  />
                                  <span className="text-gray-700">{label}</span>
                                </label>
                              );
                            })}
                        </div>
                      </div>
                    )}

                    {/* Organizations */}
                    {organizations.length > 0 && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700">Empresas (iDempiere)</label>
                        <p className="text-xs text-gray-400">Sin seleccion = acceso a todas</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3">
                          {organizations.map((org) => {
                            const selected = editForm.allowed_org_ids.split(",").filter(Boolean).includes(String(org.id));
                            return (
                              <label key={org.id} className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${selected ? "bg-santoni-50 border border-santoni-200" : "hover:bg-gray-50"}`}>
                                <input
                                  type="checkbox"
                                  checked={selected}
                                  onChange={() => {
                                    const ids = editForm.allowed_org_ids.split(",").filter(Boolean);
                                    const idStr = String(org.id);
                                    const next = selected ? ids.filter((x) => x !== idStr) : [...ids, idStr];
                                    setEditForm({ ...editForm, allowed_org_ids: next.join(",") });
                                  }}
                                  className="rounded border-gray-300 text-santoni-600 focus:ring-santoni-500"
                                />
                                <span className="text-gray-700">{org.name}</span>
                                <span className="text-gray-400 text-xs">({org.value})</span>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Salesrep for vendedor */}
                    {editForm.role === "vendedor" && salesreps.length > 0 && (
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700">Vendedor en iDempiere</label>
                        <select
                          value={editForm.idempiere_salesrep_id ?? ""}
                          onChange={(e) => setEditForm({ ...editForm, idempiere_salesrep_id: e.target.value ? Number(e.target.value) : null })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-santoni-500 focus:border-santoni-500"
                        >
                          <option value="">-- Seleccionar vendedor --</option>
                          {salesreps.map((rep) => (
                            <option key={rep.id} value={rep.id}>{rep.name}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Sensitivity level */}
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">Nivel de acceso a datos</label>
                      <div className="space-y-2">
                        {[
                          { value: 0, label: "Basico", desc: "Datos operativos (ventas, produccion, compras)", color: "bg-green-100 text-green-800 border-green-300" },
                          { value: 1, label: "Financiero", desc: "Datos contables y financieros", color: "bg-blue-100 text-blue-800 border-blue-300" },
                          { value: 2, label: "Confidencial", desc: "Nomina, salarios, datos personales (RRHH)", color: "bg-red-100 text-red-800 border-red-300" },
                        ].map((level) => (
                          <label
                            key={level.value}
                            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                              editForm.sensitivity_level === level.value ? level.color : "bg-white border-gray-200 hover:bg-gray-50"
                            }`}
                          >
                            <input
                              type="radio"
                              name="edit_sensitivity_level"
                              value={level.value}
                              checked={editForm.sensitivity_level === level.value}
                              onChange={() => setEditForm({ ...editForm, sensitivity_level: level.value })}
                              className="text-santoni-600 focus:ring-santoni-500"
                            />
                            <div>
                              <div className="text-sm font-medium">{level.label}</div>
                              <div className="text-xs opacity-70">{level.desc}</div>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Active toggle */}
                    <div className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg">
                      <input
                        type="checkbox"
                        checked={editForm.is_active}
                        onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                        className="rounded border-gray-300 text-santoni-600 focus:ring-santoni-500"
                      />
                      <div>
                        <div className="text-sm font-medium text-gray-700">Usuario activo</div>
                        <div className="text-xs text-gray-400">Desactivar impide que el usuario inicie sesion</div>
                      </div>
                    </div>

                    {/* New password */}
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">
                        <KeyRound size={14} className="inline mr-1" />
                        Nueva contraseña (dejar vacio para no cambiar)
                      </label>
                      <input
                        type="password"
                        value={editForm.new_password}
                        onChange={(e) => setEditForm({ ...editForm, new_password: e.target.value })}
                        className="input-field"
                        placeholder="Min 8 caracteres, mayuscula, minuscula, numero, especial"
                      />
                    </div>

                    <div className="flex gap-2 pt-2">
                      <button
                        type="submit"
                        disabled={editLoading || !editForm.admin_password}
                        className="btn-primary text-sm disabled:opacity-50"
                      >
                        {editLoading ? "Guardando..." : "Guardar cambios"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingUser(null)}
                        className="btn-secondary text-sm"
                      >
                        Cancelar
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Security Tab */}
        {tab === "security" && (
          <SecurityPanel user={user} />
        )}

        {/* Metrics Tab */}
        {tab === "metrics" && (
          <MetricsPanel />
        )}

        {/* Audit Logs Tab */}
        {tab === "logs" && (
          <AuditPanel auditLogs={auditLogs} users={users} />
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

function MetricsPanel() {
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

function AuditPanel({
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

  // Filters
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

  // If viewing conversations for a user, show that view
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

  // Filter and sort users
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

  // Get unique departments and roles from users
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

function StatCard({
  label,
  value,
  total,
  icon: Icon,
}: {
  label: string;
  value: number;
  total?: number;
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
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
