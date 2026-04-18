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
  Lock,
} from "lucide-react";
import Link from "next/link";
import { DEPARTMENT_LABELS, ROLE_LABELS } from "@/components/admin/constants";
import SecurityPanel from "@/components/admin/SecurityPanel";
import MetricsPanel from "@/components/admin/MetricsPanel";
import AuditPanel from "@/components/admin/AuditPanel";
import StatCard from "@/components/admin/StatCard";

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
