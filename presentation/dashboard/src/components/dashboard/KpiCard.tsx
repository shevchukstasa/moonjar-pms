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
  variant?: 'default' | 'glass';
}

const colorMap = {
  blue: 'bg-blue-50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800/30',
  green: 'bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800/30',
  yellow: 'bg-yellow-50 border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800/30',
  red: 'bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800/30',
  purple: 'bg-purple-50 border-purple-200 dark:bg-purple-950/30 dark:border-purple-800/30',
};

const glassStyle = 'bg-white/70 dark:bg-stone-900/40 backdrop-blur-xl border-white/20 dark:border-white/10 shadow-lg';

export function KpiCard({ title, value, subtitle, trend, icon, className, color = 'blue', variant = 'default' }: KpiCardProps) {
  return (
    <div className={cn('rounded-lg border p-3 md:p-4 shadow-sm', variant === 'glass' ? glassStyle : colorMap[color], className)}>
      <div className="flex items-center justify-between">
        <p className="text-[10px] md:text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{title}</p>
        {icon && <div className="text-gray-400 dark:text-gray-500">{icon}</div>}
      </div>
      <div className="mt-1 md:mt-2 flex items-baseline gap-2">
        <p className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
        {trend !== undefined && (
          <span className={cn(
            'inline-flex items-center gap-0.5 text-xs font-medium',
            trend > 0 ? 'text-green-600 dark:text-green-400' : trend < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400',
          )}>
            {trend > 0 ? <TrendingUp className="h-3 w-3" /> : trend < 0 ? <TrendingDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
            {Math.abs(trend).toFixed(1)}%
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>}
    </div>
  );
}
