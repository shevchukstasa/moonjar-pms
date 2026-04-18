/**
 * Inline design picker — visual tile selector for a material's 3D/variant design.
 *
 * Shows available designs as small tiles (photo or DesignPlaceholder). User
 * taps to select. "None" option clears the selection.
 *
 * Works without any photos uploaded — placeholder carries the design name.
 */
import { useState } from 'react';
import { useDesigns, useCreateDesign } from '@/hooks/useDesigns';
import { DesignPlaceholder } from './DesignPlaceholder';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface Props {
  value: string | null | undefined;  // design_id
  onChange: (designId: string | null) => void;
  typology: string | null | undefined;
}

export function DesignPicker({ value, onChange, typology }: Props) {
  const [adding, setAdding] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [error, setError] = useState('');

  const { data, isLoading } = useDesigns({ typology: typology || undefined });
  const createMut = useCreateDesign();

  const designs = data?.items ?? [];

  const handleCreate = async () => {
    if (!newCode.trim() || !newName.trim()) {
      setError('Код и название обязательны');
      return;
    }
    try {
      const d = await createMut.mutateAsync({
        code: newCode.trim(),
        name: newName.trim(),
        typology: typology || null,
      });
      onChange(d.id);
      setAdding(false);
      setNewCode('');
      setNewName('');
      setError('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка создания');
    }
  };

  if (isLoading) {
    return <div className="text-xs text-gray-400">Загружаю дизайны…</div>;
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {/* "None" option */}
        <button
          type="button"
          onClick={() => onChange(null)}
          className={
            'relative w-16 h-16 rounded-lg border-2 flex items-center justify-center text-xs transition ' +
            (!value
              ? 'border-primary-500 bg-primary-50 text-primary-700 dark:border-gold-500 dark:bg-gold-500/10 dark:text-gold-300'
              : 'border-gray-300 text-gray-500 hover:border-gray-400 dark:border-stone-700 dark:text-stone-400')
          }
          title="Без дизайна"
        >
          ✕
        </button>

        {/* Existing designs */}
        {designs.map((d) => (
          <button
            type="button"
            key={d.id}
            onClick={() => onChange(d.id)}
            title={`${d.name} (${d.code})`}
            className={
              'relative w-16 h-16 rounded-lg overflow-hidden border-2 transition ' +
              (value === d.id
                ? 'border-primary-500 ring-2 ring-primary-200 dark:border-gold-500 dark:ring-gold-500/30'
                : 'border-gray-200 hover:border-gray-400 dark:border-stone-700')
            }
          >
            {d.photo_url ? (
              <img src={d.photo_url} alt={d.name} className="w-full h-full object-cover" />
            ) : (
              <DesignPlaceholder code={d.code} name={d.name} size="sm" />
            )}
            {value === d.id && (
              <div className="absolute inset-0 flex items-end justify-center pb-1">
                <span className="text-[10px] font-semibold text-white drop-shadow">✓</span>
              </div>
            )}
          </button>
        ))}

        {/* Add new */}
        {!adding && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 text-gray-400 flex items-center justify-center text-2xl hover:border-gold-500 hover:text-gold-500 dark:border-stone-700 transition"
            title="Новый дизайн"
          >
            +
          </button>
        )}
      </div>

      {/* Selected design label */}
      {value && (
        <p className="text-xs text-gray-500 dark:text-stone-400">
          Выбран: <span className="font-medium">
            {designs.find((d) => d.id === value)?.name ?? '(не найден)'}
          </span>
        </p>
      )}

      {/* Inline new-design form */}
      {adding && (
        <div className="mt-2 p-3 rounded-lg border border-gray-200 bg-gray-50 dark:bg-stone-800 dark:border-stone-700 space-y-2">
          <div className="text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-stone-400">
            Новый дизайн
          </div>
          {error && <div className="text-xs text-red-600">{error}</div>}
          <div className="grid grid-cols-2 gap-2">
            <Input
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              placeholder="код (design-3)"
            />
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="название (Дизайн 3)"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button
              variant="secondary"
              onClick={() => { setAdding(false); setError(''); }}
            >
              Отмена
            </Button>
            <Button onClick={handleCreate} disabled={createMut.isPending}>
              Создать и выбрать
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
