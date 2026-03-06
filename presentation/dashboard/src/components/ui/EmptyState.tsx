export function EmptyState({ title, description }: { title: string; description?: string }) {
  return <div className="flex flex-col items-center justify-center py-12 text-center"><h3 className="text-lg font-medium text-gray-900">{title}</h3>{description && <p className="mt-1 text-sm text-gray-500">{description}</p>}</div>;
}
