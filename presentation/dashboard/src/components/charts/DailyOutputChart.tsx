import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { DailyOutput } from '@/api/analytics';

interface DailyOutputChartProps {
  data: DailyOutput[];
  height?: number;
}

export function DailyOutputChart({ data, height = 300 }: DailyOutputChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    label: d.date.slice(5), // MM-DD
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value: number, name: string) => [
            name === 'output_sqm' ? `${value.toFixed(1)} m²` : `${value} pcs`,
            name === 'output_sqm' ? 'Output m²' : 'Pieces',
          ]}
          labelFormatter={(label: string) => `Date: ${label}`}
        />
        <Line type="monotone" dataKey="output_sqm" name="output_sqm" stroke="#3b82f6" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
