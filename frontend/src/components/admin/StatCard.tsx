export default function StatCard({
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
