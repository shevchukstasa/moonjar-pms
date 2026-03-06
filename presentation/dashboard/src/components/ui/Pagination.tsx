import { Button } from './Button';

export function Pagination({ page, totalPages, onPageChange }: { page: number; totalPages: number; onPageChange: (p: number) => void }) {
  return (
    <div className="flex items-center gap-2">
      <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</Button>
      <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
      <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</Button>
    </div>
  );
}
