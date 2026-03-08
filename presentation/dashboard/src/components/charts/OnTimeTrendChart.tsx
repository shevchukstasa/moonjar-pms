import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { TrendDataPoint } from '@/api/analytics';

interface OnTimeTrendChartProps {
  data: TrendDataPoint[];
  height?: number;
}

export function OnTimeTrendChart({ data, height = 300 }: OnTimeTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
        <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, 'On-Time Rate']} />
        <ReferenceLine y={90} stroke="#22c55e" strokeDasharray="3 3" label="Target" />
        <Line type="monotone" dataKey="value" name="On-Time %" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
