import type { FinancialSummary } from '@/api/financials';
import { DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/cn';

interface FinancialBlockProps {
  data: FinancialSummary;
  className?: string;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

export function FinancialBlock({ data, className }: FinancialBlockProps) {
  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white p-4 shadow-sm', className)}>
      <h3 className="mb-4 text-sm font-semibold text-gray-900 flex items-center gap-2">
        <DollarSign className="h-4 w-4" />
        Financial Summary
      </h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div>
          <p className="text-xs text-gray-500">OPEX</p>
          <p className="text-lg font-bold text-gray-900">{formatCurrency(data.opex_total)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">CAPEX</p>
          <p className="text-lg font-bold text-gray-900">{formatCurrency(data.capex_total)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Revenue</p>
          <p className="text-lg font-bold text-green-700">{formatCurrency(data.revenue)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Margin</p>
          <div className="flex items-baseline gap-1">
            <p className={cn('text-lg font-bold', data.margin >= 0 ? 'text-green-700' : 'text-red-600')}>
              {formatCurrency(data.margin)}
            </p>
            <span className={cn('text-xs', data.margin_percent >= 0 ? 'text-green-600' : 'text-red-500')}>
              {data.margin >= 0 ? <TrendingUp className="inline h-3 w-3" /> : <TrendingDown className="inline h-3 w-3" />}
              {data.margin_percent.toFixed(1)}%
            </span>
          </div>
        </div>
        <div>
          <p className="text-xs text-gray-500">Cost/m²</p>
          <p className="text-lg font-bold text-gray-900">${data.cost_per_sqm.toFixed(2)}</p>
        </div>
      </div>
      {data.breakdown.length > 0 && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          <p className="mb-2 text-xs font-medium text-gray-500">OPEX Breakdown</p>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {data.breakdown
              .filter((b) => b.entry_type === 'opex')
              .map((b) => (
                <div key={b.category} className="text-xs">
                  <p className="text-gray-500 capitalize">{b.category}</p>
                  <p className="font-medium text-gray-900">{formatCurrency(b.total)}</p>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
