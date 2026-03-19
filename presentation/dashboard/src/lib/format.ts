import { format, formatDistanceToNow, parseISO } from 'date-fns';

export function formatDate(date: string | Date): string {
  return format(typeof date === 'string' ? parseISO(date) : date, 'dd/MM/yyyy');
}
export function formatDateTime(date: string | Date): string {
  return format(typeof date === 'string' ? parseISO(date) : date, 'dd/MM/yyyy HH:mm');
}
export function formatRelative(date: string | Date): string {
  return formatDistanceToNow(typeof date === 'string' ? parseISO(date) : date, { addSuffix: true });
}
export function formatNumber(n: number, decimals = 0): string {
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(n);
}
export function formatArea(sqm: number): string { return `${formatNumber(sqm, 2)} m\u00B2`; }
