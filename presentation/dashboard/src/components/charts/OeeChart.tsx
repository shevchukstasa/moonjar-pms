import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface OeeChartProps {
  data: { label: string; oee: number }[];
  height?: number;
}

export function OeeChart({ data, height = 200 }: OeeChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10 }} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
        <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, 'OEE']} />
        <ReferenceLine y={85} stroke="#22c55e" strokeDasharray="3 3" label="Target" />
        <Area type="monotone" dataKey="oee" name="OEE %" stroke="#8b5cf6" fill="#ede9fe" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
