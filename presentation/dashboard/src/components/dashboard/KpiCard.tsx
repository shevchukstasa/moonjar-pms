import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/cn';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: number;
  icon?: React.ReactNode;
  className?: string;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
}

const colorMap = {
  blue: 'bg-blue-50 border-blue-200',
  green: 'bg-green-50 border-green-200',
  yellow: 'bg-yellow-50 border-yellow-200',
  red: 'bg-red-50 border-red-200',
  purple: 'bg-purple-50 border-purple-200',
};

export function KpiCard({ title, value, subtitle, trend, icon, className, color = 'blue' }: KpiCardProps) {
  return (
    <div className={cn('rounded-lg border p-4 shadow-sm', colorMap[color], className)}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {trend !== undefined && (
          <span className={cn(
            'inline-flex items-center gap-0.5 text-xs font-medium',
            trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500',
          )}>
            {trend > 0 ? <TrendingUp className="h-3 w-3" /> : trend < 0 ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
            {Math.abs(trend).toFixed(1)}%
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
    </div>
  );
}
