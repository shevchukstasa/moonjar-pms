import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { CHART_COLORS } from '@/lib/chartTheme';

interface OeeChartProps {
  data: { label: string; oee: number }[];
  height?: number;
}

export function OeeChart({ data, height = 200 }: OeeChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.gridLight} />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: CHART_COLORS.textLight }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: CHART_COLORS.textLight }} unit="%" />
        <Tooltip
          formatter={(value: number) => [`${value.toFixed(1)}%`, 'OEE']}
          contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
        />
        <ReferenceLine y={85} stroke={CHART_COLORS.success} strokeDasharray="3 3" label="Target" />
        <Area type="monotone" dataKey="oee" name="OEE %" stroke={CHART_COLORS.gold} fill={`${CHART_COLORS.gold}20`} strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
