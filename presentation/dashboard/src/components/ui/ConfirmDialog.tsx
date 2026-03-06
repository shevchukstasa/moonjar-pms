import { Dialog } from './Dialog';
import { Button } from './Button';
export function ConfirmDialog({ open, onClose, onConfirm, title, message }: { open: boolean; onClose: () => void; onConfirm: () => void; title: string; message: string }) {
  return <Dialog open={open} onClose={onClose} title={title}><p className="mb-4 text-sm text-gray-600">{message}</p><div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button variant="danger" onClick={() => { onConfirm(); onClose(); }}>Confirm</Button></div></Dialog>;
}
