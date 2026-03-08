import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DefectWeeklyChartProps {
  data: { date: string; defect_rate: number }[];
  height?: number;
}

const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function DefectWeeklyChart({ data, height = 200 }: DefectWeeklyChartProps) {
  const chartData = data.map((d, i) => ({
    ...d,
    label: dayLabels[i] || d.date.slice(5),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit="%" />
        <Tooltip formatter={(value: number) => [`${value.toFixed(2)}%`, 'Defect Rate']} />
        <Bar dataKey="defect_rate" name="Defect Rate" fill="#f97316" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
