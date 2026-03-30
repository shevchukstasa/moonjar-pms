const PRODUCTION_HINTS: Record<string, string> = {
  orders: 'No orders yet — production floor is clean',
  positions: 'All positions shipped — great work!',
  defects: 'No defects recorded — quality excellence',
};

export function EmptyState({ title, description, context }: { title: string; description?: string; context?: string }) {
  const hint = context ? PRODUCTION_HINTS[context] : undefined;
  return (
    <div
      className="flex flex-col items-center justify-center py-12 text-center rounded-lg"
      style={{
        background: 'radial-gradient(ellipse at 50% 0%, rgba(168,162,158,0.08) 0%, transparent 70%)',
      }}
    >
      <h3 className="text-lg font-medium text-gray-900 dark:text-stone-100">{title}</h3>
      {description && <p className="mt-1 text-sm text-gray-500 dark:text-stone-500">{description}</p>}
      {hint && <p className="mt-3 text-xs text-stone-400 dark:text-stone-500 italic">{hint}</p>}
    </div>
  );
}
