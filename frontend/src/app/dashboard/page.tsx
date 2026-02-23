"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import Link from "next/link";
import {
  ArrowLeft,
  MessageSquare,
  TrendingUp,
  AlertTriangle,
  DollarSign,
  Users,
  ShoppingCart,
  Factory,
  BarChart3,
  Clock,
  RefreshCw,
  ChevronRight,
  Bell,
} from "lucide-react";

const DEPARTMENT_LABELS: Record<string, string> = {
  finanzas: "Finanzas",
  contabilidad: "Contabilidad",
  ventas: "Ventas",
  rrhh: "RRHH",
  produccion: "Produccion",
  compras_insumos: "Compras Insumos",
  compras_productores: "Compras Productores",
};

const DEPT_ICONS: Record<string, typeof DollarSign> = {
  finanzas: DollarSign,
  contabilidad: BarChart3,
  ventas: TrendingUp,
  rrhh: Users,
  produccion: Factory,
  compras_insumos: ShoppingCart,
  compras_productores: ShoppingCart,
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("es-VE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [kpis, setKpis] = useState<Record<string, unknown> | null>(null);
  const [activity, setActivity] = useState<{
    conversations: number;
    messages_7d: number;
  } | null>(null);
  const [alerts, setAlerts] = useState<
    Array<{
      type: string;
      department: string;
      title: string;
      message: string;
      value: number;
    }>
  >([]);
  const [timestamp, setTimestamp] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (user) loadDashboard();
  }, [user]);

  const loadDashboard = async () => {
    setRefreshing(true);
    try {
      const [dashData, alertData] = await Promise.all([
        api.getDashboardKPIs(),
        api.getDashboardAlerts(),
      ]);
      setKpis(dashData.kpis);
      setActivity(dashData.activity);
      setTimestamp(
        new Date(dashData.timestamp).toLocaleString("es-VE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      );
      setAlerts(alertData.alerts);
    } catch {
      // ignore
    } finally {
      setRefreshing(false);
    }
  };

  if (loading || !user) return null;

  const DeptIcon = DEPT_ICONS[user.department] || BarChart3;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-4">
            <Link
              href="/chat"
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              <ArrowLeft size={20} />
            </Link>
            <img
              src="/santoni-logo.png"
              alt="Santoni"
              className="h-8 w-auto"
            />
            <div>
              <h1 className="text-lg font-semibold">Dashboard</h1>
              <p className="text-xs text-gray-500">
                {DEPARTMENT_LABELS[user.department] || user.department} &middot;{" "}
                {user.full_name}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {timestamp && (
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Clock size={12} />
                Actualizado: {timestamp}
              </span>
            )}
            <button
              onClick={loadDashboard}
              disabled={refreshing}
              className="p-2 rounded-lg text-gray-400 hover:text-santoni-600 hover:bg-santoni-50 transition-colors"
              title="Actualizar"
            >
              <RefreshCw
                size={16}
                className={refreshing ? "animate-spin" : ""}
              />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Quick navigation */}
        <div className="flex gap-2">
          <Link
            href="/chat"
            className="flex items-center gap-2 px-4 py-2 bg-santoni-600 text-white rounded-lg text-sm font-medium hover:bg-santoni-700 transition-colors"
          >
            <MessageSquare size={16} />
            Ir al Chat
            <ChevronRight size={14} />
          </Link>
          {user.role === "administrador" && (
            <Link
              href="/admin"
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              <BarChart3 size={16} />
              Panel Admin
            </Link>
          )}
        </div>

        {/* Alerts banner */}
        {alerts.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Bell size={18} className="text-amber-600" />
              <h2 className="font-semibold text-amber-800">
                Alertas ({alerts.length})
              </h2>
            </div>
            <div className="space-y-2">
              {alerts.map((alert, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 bg-white rounded-lg p-3 border border-amber-100"
                >
                  <AlertTriangle
                    size={16}
                    className="text-amber-500 mt-0.5 shrink-0"
                  />
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {alert.title}
                    </div>
                    <div className="text-xs text-gray-500">
                      {alert.message}
                    </div>
                  </div>
                  <span className="ml-auto text-xs text-gray-400 whitespace-nowrap">
                    {DEPARTMENT_LABELS[alert.department] || alert.department}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Activity cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Mi actividad</span>
              <MessageSquare size={18} className="text-santoni-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {activity?.conversations || 0}
            </div>
            <div className="text-xs text-gray-400">conversaciones totales</div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Ultimos 7 dias</span>
              <TrendingUp size={18} className="text-green-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {activity?.messages_7d || 0}
            </div>
            <div className="text-xs text-gray-400">mensajes enviados</div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">Departamento</span>
              <DeptIcon size={18} className="text-santoni-500" />
            </div>
            <div className="text-lg font-bold text-gray-900">
              {DEPARTMENT_LABELS[user.department] || user.department}
            </div>
            <div className="text-xs text-gray-400">{user.role}</div>
          </div>
        </div>

        {/* Department KPIs */}
        {kpis && Object.keys(kpis).length > 0 && !kpis.error && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <DeptIcon size={20} className="text-santoni-600" />
              KPIs - {DEPARTMENT_LABELS[user.department] || user.department}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Ventas KPIs */}
              {kpis.ventas_mes && (
                <KPICard
                  label="Ventas del Mes"
                  value={`Bs. ${formatCurrency(
                    (kpis.ventas_mes as { valor: number }).valor
                  )}`}
                  subtitle={`${
                    (kpis.ventas_mes as { facturas: number }).facturas
                  } facturas`}
                  color="green"
                />
              )}
              {kpis.cxc_vencidas && (
                <KPICard
                  label="CxC Vencidas (+30d)"
                  value={`Bs. ${formatCurrency(
                    (kpis.cxc_vencidas as { valor: number }).valor
                  )}`}
                  subtitle={`${
                    (kpis.cxc_vencidas as { facturas: number }).facturas
                  } facturas`}
                  color="red"
                />
              )}
              {kpis.top_clientes &&
                Array.isArray(kpis.top_clientes) &&
                (kpis.top_clientes as Array<{ nombre: string; total: number }>)
                  .length > 0 && (
                  <div className="sm:col-span-2 lg:col-span-1">
                    <div className="text-xs font-medium text-gray-500 mb-2">
                      Top Clientes del Mes
                    </div>
                    <div className="space-y-1">
                      {(
                        kpis.top_clientes as Array<{
                          nombre: string;
                          total: number;
                        }>
                      )
                        .slice(0, 5)
                        .map((c, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between text-xs"
                          >
                            <span className="text-gray-600 truncate max-w-[150px]">
                              {i + 1}. {c.nombre}
                            </span>
                            <span className="text-gray-900 font-medium">
                              Bs. {formatCurrency(c.total)}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

              {/* Finanzas KPIs */}
              {kpis.cxp_pendientes && (
                <KPICard
                  label="CxP Pendientes"
                  value={`Bs. ${formatCurrency(
                    (kpis.cxp_pendientes as { valor: number }).valor
                  )}`}
                  subtitle={`${
                    (kpis.cxp_pendientes as { facturas: number }).facturas
                  } facturas`}
                  color="orange"
                />
              )}
              {typeof kpis.cuentas_bancarias === "number" && (
                <KPICard
                  label="Cuentas Bancarias"
                  value={String(kpis.cuentas_bancarias)}
                  subtitle="activas"
                  color="blue"
                />
              )}

              {/* Compras KPIs */}
              {kpis.compras_mes && (
                <KPICard
                  label="Compras del Mes"
                  value={`Bs. ${formatCurrency(
                    (kpis.compras_mes as { valor: number }).valor
                  )}`}
                  subtitle={`${
                    (kpis.compras_mes as { facturas: number }).facturas
                  } facturas`}
                  color="purple"
                />
              )}

              {/* Contabilidad */}
              {typeof kpis.asientos_mes === "number" && (
                <KPICard
                  label="Asientos Contables"
                  value={String(kpis.asientos_mes)}
                  subtitle="este mes"
                  color="blue"
                />
              )}

              {/* RRHH */}
              {typeof kpis.empleados_activos === "number" && (
                <KPICard
                  label="Empleados Activos"
                  value={String(kpis.empleados_activos)}
                  subtitle="en iDempiere"
                  color="green"
                />
              )}

              {/* Produccion note */}
              {kpis.nota && (
                <div className="text-xs text-gray-400 italic p-3">
                  {String(kpis.nota)}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">
            Consultas rapidas
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {getQuickQueries(user.department).map((q) => (
              <Link
                key={q}
                href="/chat"
                onClick={() => {
                  sessionStorage.setItem("santonibot_prefill", q);
                }}
                className="text-left p-3 rounded-lg border border-gray-200 hover:bg-santoni-50 hover:border-santoni-300 transition-colors text-sm text-gray-600"
              >
                {q}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICard({
  label,
  value,
  subtitle,
  color,
}: {
  label: string;
  value: string;
  subtitle: string;
  color: "green" | "red" | "blue" | "orange" | "purple";
}) {
  const colorMap = {
    green: "bg-green-50 text-green-700 border-green-200",
    red: "bg-red-50 text-red-700 border-red-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    orange: "bg-orange-50 text-orange-700 border-orange-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
  };

  return (
    <div className={`rounded-lg border p-4 ${colorMap[color]}`}>
      <div className="text-xs font-medium opacity-80 mb-1">{label}</div>
      <div className="text-lg font-bold">{value}</div>
      <div className="text-xs opacity-60">{subtitle}</div>
    </div>
  );
}

function getQuickQueries(department: string): string[] {
  const queries: Record<string, string[]> = {
    ventas: [
      "Top 20 clientes por ventas del mes",
      "Cobranzas pendientes vencidas",
      "Ventas por zona esta semana",
      "Ranking de vendedores del mes",
    ],
    finanzas: [
      "Flujo de caja del mes",
      "Saldo de bancos actualizado",
      "Cuentas por pagar proximas a vencer",
      "Resumen de cuentas por cobrar",
    ],
    contabilidad: [
      "Balance general actualizado",
      "Estado de resultados del mes",
      "Balance de comprobacion",
      "Libro mayor resumido",
    ],
    rrhh: [
      "Empleados por departamento",
      "Resumen de nomina del mes",
      "Vacaciones pendientes",
      "Reporte de asistencia semanal",
    ],
    produccion: [
      "Produccion de hoy",
      "Eficiencia OEE del mes",
      "Desperdicio de la semana",
      "Ordenes de produccion pendientes",
    ],
    compras_insumos: [
      "Compras de insumos del mes",
      "Ordenes de compra pendientes",
      "Top proveedores por monto",
      "Inventario de materiales",
    ],
    compras_productores: [
      "Compras de arroz paddy del mes",
      "Compras de maiz del mes",
      "Top productores por volumen",
      "Pagos pendientes a productores",
    ],
  };
  return queries[department] || queries.ventas;
}
