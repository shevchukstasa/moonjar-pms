import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { CHART_COLORS } from '@/lib/chartTheme';
import type { TrendDataPoint } from '@/api/analytics';

interface OutputTrendChartProps {
  data: TrendDataPoint[];
  height?: number;
}

export function OutputTrendChart({ data, height = 300 }: OutputTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.gridLight} />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: CHART_COLORS.textLight }} />
        <YAxis tick={{ fontSize: 12, fill: CHART_COLORS.textLight }} />
        <Tooltip
          formatter={(value: number) => [`${value.toFixed(0)} m²`, 'Output']}
          contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
        />
        <Legend />
        <Bar dataKey="value" name="Output (m²)" fill={CHART_COLORS.copper} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
