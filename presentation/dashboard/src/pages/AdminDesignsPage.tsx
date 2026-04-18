/**
 * Stone Designs gallery — 3D variants / patterns catalog.
 *
 * Visual tile gallery (not a boring table). Each design shows photo or
 * warm stone-like placeholder if photo is absent. System must remain
 * usable without any photos uploaded.
 *
 * Access: owner/administrator only.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useDesigns,
  useCreateDesign,
  useUpdateDesign,
  useDeleteDesign,
  type StoneDesign,
  type DesignCreateInput,
} from '@/hooks/useDesigns';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Dialog } from '@/components/ui/Dialog';
import { Spinner } from '@/components/ui/Spinner';
import { Select } from '@/components/ui/Select';
import { DesignPlaceholder } from '@/components/material/DesignPlaceholder';

const TYPOLOGY_OPTIONS = [
  { value: '', label: 'Все типологии' },
  { value: '3d', label: '3D' },
  { value: 'tiles', label: 'Плоская плитка' },
  { value: 'sink', label: 'Sink' },
  { value: 'countertop', label: 'Countertop' },
  { value: 'freeform', label: 'Freeform' },
];

export default function AdminDesignsPage() {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<StoneDesign | null>(null);
  const [form, setForm] = useState<DesignCreateInput>({
    code: '', name: '', name_id: '', typology: '3d', photo_url: '', description: '',
  });
  const [error, setError] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading } = useDesigns({ include_inactive: true });
  const createMut = useCreateDesign();
  const updateMut = useUpdateDesign();
  const deleteMut = useDeleteDesign();

  const items = data?.items ?? [];

  const openCreate = () => {
    setEditing(null);
    setForm({ code: '', name: '', name_id: '', typology: '3d', photo_url: '', description: '' });
    setError('');
    setDialogOpen(true);
  };

  const openEdit = (d: StoneDesign) => {
    setEditing(d);
    setForm({
      code: d.code,
      name: d.name,
      name_id: d.name_id ?? '',
      typology: d.typology ?? '',
      photo_url: d.photo_url ?? '',
      description: d.description ?? '',
    });
    setError('');
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.code.trim() || !form.name.trim()) {
      setError('Код и название обязательны');
      return;
    }
    try {
      const payload: DesignCreateInput = {
        code: form.code.trim(),
        name: form.name.trim(),
        name_id: form.name_id?.trim() || null,
        typology: form.typology || null,
        photo_url: form.photo_url?.trim() || null,
        description: form.description?.trim() || null,
      };
      if (editing) {
        await updateMut.mutateAsync({ id: editing.id, data: payload });
      } else {
        await createMut.mutateAsync(payload);
      }
      setDialogOpen(false);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка сохранения');
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteMut.mutateAsync(deleteId);
      setDeleteId(null);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Нельзя удалить');
      setDeleteId(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            type="button"
            onClick={() => navigate('/admin')}
            className="text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            ← Admin Panel
          </button>
          <h1 className="text-3xl font-serif tracking-tight text-gray-900 dark:text-stone-100">
            Каталог дизайнов
          </h1>
          <p className="text-sm text-gray-500 dark:text-stone-400 mt-1">
            3D-узоры и варианты — различают материалы одного размера
          </p>
        </div>
        <Button onClick={openCreate}>+ Добавить дизайн</Button>
      </div>

      {isLoading ? (
        <div className="py-20 flex justify-center"><Spinner /></div>
      ) : items.length === 0 ? (
        <EmptyState onCreate={openCreate} />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
          {items.map((d) => (
            <DesignCard
              key={d.id}
              design={d}
              onEdit={() => openEdit(d)}
              onDelete={() => setDeleteId(d.id)}
            />
          ))}
          {/* Add-new tile */}
          <button
            type="button"
            onClick={openCreate}
            className="aspect-square rounded-xl border-2 border-dashed border-gray-300 dark:border-stone-700 flex flex-col items-center justify-center gap-2 text-gray-400 hover:border-gold-500 hover:text-gold-600 dark:hover:border-gold-400 dark:hover:text-gold-400 transition"
          >
            <span className="text-4xl">+</span>
            <span className="text-sm">Новый дизайн</span>
          </button>
        </div>
      )}

      {/* Edit/create dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title={editing ? `Редактировать: ${editing.name}` : 'Новый дизайн'}
      >
        <div className="space-y-4 max-w-md">
          {error && (
            <div className="px-3 py-2 bg-red-50 text-red-700 text-sm rounded">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">
              Код <span className="text-red-500">*</span>
              <span className="text-xs text-gray-500 font-normal ml-2">
                (короткий, латиницей — &laquo;wave&raquo;, &laquo;bumpy&raquo;)
              </span>
            </label>
            <Input
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="design-1"
              disabled={!!editing}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Название <span className="text-red-500">*</span>
            </label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Дизайн 1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Название (индонезийский)
              <span className="text-xs text-gray-500 font-normal ml-2">
                для мастеров
              </span>
            </label>
            <Input
              value={form.name_id ?? ''}
              onChange={(e) => setForm({ ...form, name_id: e.target.value })}
              placeholder="Desain 1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Типология</label>
            <Select
              value={form.typology ?? ''}
              onChange={(e) => setForm({ ...form, typology: e.target.value })}
              options={TYPOLOGY_OPTIONS}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              URL фото
              <span className="text-xs text-gray-500 font-normal ml-2">
                опционально — без фото тоже работает
              </span>
            </label>
            <Input
              value={form.photo_url ?? ''}
              onChange={(e) => setForm({ ...form, photo_url: e.target.value })}
              placeholder="https://..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Описание</label>
            <textarea
              value={form.description ?? ''}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Короткая заметка для мастеров"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm dark:bg-stone-800 dark:border-stone-700"
              rows={3}
            />
          </div>

          <div className="flex gap-2 justify-end pt-2">
            <Button variant="secondary" onClick={() => setDialogOpen(false)}>
              Отмена
            </Button>
            <Button
              onClick={handleSave}
              disabled={createMut.isPending || updateMut.isPending}
            >
              {editing ? 'Сохранить' : 'Создать'}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Удалить дизайн?"
      >
        <div className="space-y-4 max-w-sm">
          <p className="text-sm text-gray-600">
            Нельзя будет отменить. Если дизайн используется в материалах — удаление не пройдёт.
          </p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setDeleteId(null)}>Отмена</Button>
            <Button variant="danger" onClick={handleDelete} disabled={deleteMut.isPending}>
              Удалить
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────────

function DesignCard({
  design: d,
  onEdit,
  onDelete,
}: {
  design: StoneDesign;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="group relative rounded-xl overflow-hidden bg-white dark:bg-stone-900 shadow-sm hover:shadow-xl transition-all duration-300 border border-gray-200 dark:border-stone-800">
      {/* Visual */}
      <div className="aspect-square relative">
        {d.photo_url ? (
          <img
            src={d.photo_url}
            alt={d.name}
            className="w-full h-full object-cover"
            onError={(e) => ((e.currentTarget as HTMLImageElement).style.display = 'none')}
          />
        ) : (
          <DesignPlaceholder code={d.code} name={d.name} size="lg" />
        )}
        {/* Typology badge */}
        {d.typology && (
          <span className="absolute top-2 right-2 px-2 py-0.5 text-xs font-medium bg-black/50 text-white rounded-full backdrop-blur-sm">
            {d.typology}
          </span>
        )}
        {/* Inactive overlay */}
        {!d.is_active && (
          <div className="absolute inset-0 bg-white/60 dark:bg-black/60 flex items-center justify-center">
            <span className="px-3 py-1 bg-gray-800 text-white text-xs rounded-full">Неактивен</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-1">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="font-medium text-gray-900 dark:text-stone-100 truncate">
            {d.name}
          </h3>
          <span className="text-xs font-mono text-gray-400 flex-shrink-0">{d.code}</span>
        </div>
        {d.name_id && (
          <p className="text-xs text-gray-500 dark:text-stone-400 italic truncate">{d.name_id}</p>
        )}
        <p className="text-xs text-gray-500 dark:text-stone-400">
          {d.material_count > 0
            ? `${d.material_count} материал${d.material_count === 1 ? '' : 'ов'}`
            : 'ещё не используется'}
        </p>
      </div>

      {/* Hover actions */}
      <div className="absolute top-2 left-2 opacity-0 group-hover:opacity-100 transition flex gap-1">
        <button
          type="button"
          onClick={onEdit}
          className="px-2 py-1 text-xs bg-white/90 dark:bg-stone-800/90 rounded backdrop-blur-sm shadow hover:bg-white dark:hover:bg-stone-700"
        >
          ✎ Edit
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="px-2 py-1 text-xs bg-white/90 dark:bg-stone-800/90 rounded backdrop-blur-sm shadow hover:bg-red-50 hover:text-red-600"
        >
          🗑
        </button>
      </div>
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="py-20 text-center">
      <div className="inline-block mx-auto mb-4">
        <DesignPlaceholder code="empty" name="◆" size="lg" />
      </div>
      <h2 className="text-xl font-serif mb-2 text-gray-800 dark:text-stone-200">
        Пока ни одного дизайна
      </h2>
      <p className="text-sm text-gray-500 dark:text-stone-400 mb-6 max-w-sm mx-auto">
        Создайте первый, чтобы различать материалы одного размера (например, две 3D-плитки 5×20×1-2 с разным рельефом)
      </p>
      <Button onClick={onCreate}>+ Добавить первый дизайн</Button>
    </div>
  );
}
