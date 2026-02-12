"use client";

import { useRef, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Download, BarChart3, Table2 } from "lucide-react";

export interface ChartData {
  type: "bar" | "line" | "pie" | "area";
  title?: string;
  xKey: string;
  yKey: string | string[];
  data: Record<string, unknown>[];
}

const COLORS = [
  "#042387", // santoni blue
  "#2563eb", // blue
  "#16a34a", // green
  "#dc2626", // red
  "#9333ea", // purple
  "#ca8a04", // yellow
  "#0891b2", // cyan
  "#be185d", // pink
  "#65a30d", // lime
  "#6366f1", // indigo
];

function formatValue(value: unknown): string {
  if (typeof value === "number") {
    return value.toLocaleString("es-VE", { maximumFractionDigits: 2 });
  }
  return String(value ?? "");
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 shadow-lg rounded-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color }} className="flex justify-between gap-4">
          <span>{entry.name}:</span>
          <span className="font-medium">{formatValue(entry.value)}</span>
        </p>
      ))}
    </div>
  );
}

interface ChartRendererProps {
  chart: ChartData;
}

export default function ChartRenderer({ chart }: ChartRendererProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);

  const { type, title, xKey, data } = chart;
  const yKeys = Array.isArray(chart.yKey) ? chart.yKey : [chart.yKey];

  const handleExportPng = async () => {
    if (!chartRef.current || exporting) return;
    setExporting(true);
    try {
      const { toPng } = await import("html-to-image");
      const dataUrl = await toPng(chartRef.current, {
        backgroundColor: "#ffffff",
        pixelRatio: 2,
      });
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `santonibot_grafica_${Date.now()}.png`;
      a.click();
    } catch (err) {
      console.error("Error exporting chart:", err);
    } finally {
      setExporting(false);
    }
  };

  const truncateLabel = (label: string, maxLen = 15) =>
    label.length > maxLen ? label.slice(0, maxLen) + "..." : label;

  const renderChart = () => {
    switch (type) {
      case "bar":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey={xKey}
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => truncateLabel(String(v))}
                interval={0}
                angle={data.length > 8 ? -35 : 0}
                textAnchor={data.length > 8 ? "end" : "middle"}
                height={data.length > 8 ? 70 : 30}
              />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatValue(v)} width={70} />
              <Tooltip content={<CustomTooltip />} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
              {yKeys.map((key, i) => (
                <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case "line":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey={xKey}
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => truncateLabel(String(v))}
              />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatValue(v)} width={70} />
              <Tooltip content={<CustomTooltip />} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
              {yKeys.map((key, i) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case "area":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey={xKey}
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => truncateLabel(String(v))}
              />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatValue(v)} width={70} />
              <Tooltip content={<CustomTooltip />} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
              {yKeys.map((key, i) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[i % COLORS.length]}
                  fill={COLORS[i % COLORS.length]}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        );

      case "pie":
        return (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={data}
                dataKey={yKeys[0]}
                nameKey={xKey}
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, percent }) =>
                  `${truncateLabel(String(name), 12)} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={{ strokeWidth: 1 }}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        );

      default:
        return <p className="text-xs text-gray-500">Tipo de grafica no soportado: {type}</p>;
    }
  };

  return (
    <div className="my-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-santoni-600" />
          {title && <span className="text-xs font-semibold text-gray-700">{title}</span>}
        </div>
        <button
          onClick={handleExportPng}
          disabled={exporting}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-santoni-600 transition-colors px-2 py-1 rounded hover:bg-gray-50"
          title="Descargar grafica como imagen"
        >
          <Download size={12} />
          <span>{exporting ? "Exportando..." : "PNG"}</span>
        </button>
      </div>

      {/* Chart */}
      <div
        ref={chartRef}
        className="bg-white rounded-lg border border-gray-100 p-3"
      >
        {title && (
          <p className="text-xs font-semibold text-center text-gray-600 mb-2">{title}</p>
        )}
        {renderChart()}
      </div>
    </div>
  );
}
