export const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700', confirmed: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-yellow-100 text-yellow-700', completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700', on_hold: 'bg-orange-100 text-orange-700',
  shipped: 'bg-purple-100 text-purple-700',
};
export function getStatusColor(status: string): string { return statusColors[status] || 'bg-gray-100 text-gray-700'; }
