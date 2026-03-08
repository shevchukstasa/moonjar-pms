import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { PipelineStage } from '@/api/analytics';

interface PipelineFunnelProps {
  data: PipelineStage[];
  height?: number;
}

const stageLabels: Record<string, string> = {
  planned: 'Planned',
  sent_to_glazing: 'Glazing',
  glazed: 'Glazed',
  loaded_in_kiln: 'In Kiln',
  fired: 'Fired',
  transferred_to_sorting: 'Sorting',
  packed: 'Packed',
  ready_for_shipment: 'Ready',
};

export function PipelineFunnel({ data, height = 300 }: PipelineFunnelProps) {
  const chartData = data.map((d) => ({
    ...d,
    label: stageLabels[d.stage] || d.stage,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={70} />
        <Tooltip formatter={(value: number, name: string) => [value, name === 'count' ? 'Positions' : 'm²']} />
        <Bar dataKey="count" name="Positions" fill="#6366f1" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
