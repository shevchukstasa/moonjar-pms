import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { TrendDataPoint } from '@/api/analytics';

interface OutputTrendChartProps {
  data: TrendDataPoint[];
  height?: number;
}

export function OutputTrendChart({ data, height = 300 }: OutputTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value: number) => [`${value.toFixed(0)} m²`, 'Output']} />
        <Legend />
        <Bar dataKey="value" name="Output (m²)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
