export function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }
export function truncate(s: string, n: number) { return s.length > n ? s.slice(0, n) + '...' : s; }
