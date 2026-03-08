import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { TrendDataPoint } from '@/api/analytics';

interface DefectTrendChartProps {
  data: TrendDataPoint[];
  height?: number;
}

export function DefectTrendChart({ data, height = 300 }: DefectTrendChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 'auto']} tick={{ fontSize: 12 }} unit="%" />
        <Tooltip formatter={(value: number) => [`${value.toFixed(2)}%`, 'Defect Rate']} />
        <ReferenceLine y={5} stroke="#ef4444" strokeDasharray="3 3" label="Max Target" />
        <Line type="monotone" dataKey="value" name="Defect Rate %" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
