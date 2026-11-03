import type { LucideIcon } from 'lucide-react';

interface Props {
  icon: LucideIcon;
  label: string;
  value: string | number;
  subtitle?: string;
  color: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'cyan';
}

const colorMap = {
  blue:   'from-blue-500 to-blue-600',
  green:  'from-emerald-500 to-emerald-600',
  purple: 'from-violet-500 to-violet-600',
  orange: 'from-orange-500 to-amber-500',
  red:    'from-red-500 to-rose-600',
  cyan:   'from-cyan-500 to-teal-500',
};

const bgMap = {
  blue:   'bg-blue-50',
  green:  'bg-emerald-50',
  purple: 'bg-violet-50',
  orange: 'bg-orange-50',
  red:    'bg-red-50',
  cyan:   'bg-cyan-50',
};

export default function StatCard({ icon: Icon, label, value, subtitle, color }: Props) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>}
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${colorMap[color]} text-white shadow-sm`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}

