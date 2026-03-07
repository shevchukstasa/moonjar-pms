import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useKilnConstants, useUpdateKilnConstant, type KilnConstantItem } from '@/hooks/useKilns';

export function KilnConstantsTable() {
  const { data, isLoading } = useKilnConstants();
  const updateConstant = useUpdateKilnConstant();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const constants = data?.items || [];

  const startEdit = (c: KilnConstantItem) => {
    setEditingId(c.id);
    setEditValue(String(c.value));
  };

  const saveEdit = async (c: KilnConstantItem) => {
    const newVal = parseFloat(editValue);
    if (isNaN(newVal)) return;
    await updateConstant.mutateAsync({ id: c.id, data: { value: newVal } });
    setEditingId(null);
  };

  const cancelEdit = () => { setEditingId(null); };

  if (isLoading) {
    return <div className="flex justify-center py-4"><Spinner className="h-6 w-6" /></div>;
  }

  if (constants.length === 0) {
    return <div className="py-4 text-center text-sm text-gray-400">No kiln constants configured</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-left text-sm">
        <thead className="border-b bg-gray-50 text-xs font-medium uppercase text-gray-500">
          <tr>
            <th className="px-4 py-3">Constant</th>
            <th className="px-4 py-3">Value</th>
            <th className="px-4 py-3">Unit</th>
            <th className="px-4 py-3">Description</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {constants.map((c) => (
            <tr key={c.id} className="bg-white">
              <td className="px-4 py-3 font-mono text-xs">{c.constant_name}</td>
              <td className="px-4 py-3">
                {editingId === c.id ? (
                  <input
                    type="number"
                    step="any"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveEdit(c);
                      if (e.key === 'Escape') cancelEdit();
                    }}
                    className="w-24 rounded border border-primary-500 px-2 py-1 text-sm focus:outline-none"
                    autoFocus
                  />
                ) : (
                  <span className="font-medium">{c.value}</span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-500">{c.unit || '—'}</td>
              <td className="px-4 py-3 text-gray-500">{c.description || '—'}</td>
              <td className="px-4 py-3">
                {editingId === c.id ? (
                  <div className="flex gap-1">
                    <Button size="sm" onClick={() => saveEdit(c)} disabled={updateConstant.isPending}>
                      Save
                    </Button>
                    <Button size="sm" variant="ghost" onClick={cancelEdit}>
                      ✕
                    </Button>
                  </div>
                ) : (
                  <Button size="sm" variant="ghost" onClick={() => startEdit(c)}>
                    Edit
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
