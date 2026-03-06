export function DatePicker({ value, onChange }: { value?: string; onChange: (v: string) => void }) {
  return <input type="date" value={value || ''} onChange={(e) => onChange(e.target.value)} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />;
}
