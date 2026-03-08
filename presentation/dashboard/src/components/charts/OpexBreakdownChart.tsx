import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface OpexBreakdownChartProps {
  data: { category: string; total: number }[];
  height?: number;
}

const colors = ['#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#6b7280'];

export function OpexBreakdownChart({ data, height = 250 }: OpexBreakdownChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    label: d.category.charAt(0).toUpperCase() + d.category.slice(1),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip formatter={(value: number) => [`$${value.toFixed(0)}`, 'Amount']} />
        <Bar dataKey="total" name="OPEX" radius={[4, 4, 0, 0]}>
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
