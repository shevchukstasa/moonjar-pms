import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { CHART_COLORS } from '@/lib/chartTheme';
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
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.gridLight} />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: CHART_COLORS.textLight }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 12, fill: CHART_COLORS.textLight }} />
        <Tooltip
          formatter={(value: number, name: string) => [
            name === 'output_sqm' ? `${value.toFixed(1)} m²` : `${value} pcs`,
            name === 'output_sqm' ? 'Output m²' : 'Pieces',
          ]}
          labelFormatter={(label: string) => `Date: ${label}`}
          contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
        />
        <Line type="monotone" dataKey="output_sqm" name="output_sqm" stroke={CHART_COLORS.gold} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
