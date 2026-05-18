export const PALETTE = ['#2563eb', '#0694a2', '#7c3aed', '#059669', '#dc2626', '#d97706', '#db2777', '#0891b2'];

export function fmtNum(n, dec = 0) {
  if (n == null || n === '' || isNaN(n)) return '—';
  return Number(n).toLocaleString('id-ID', { maximumFractionDigits: dec });
}

export function fmtRp(n) {
  if (n == null || isNaN(n)) return '—';
  if (n >= 1e9) return `Rp ${fmtNum(n / 1e9, 2)} M`;
  if (n >= 1e6) return `Rp ${fmtNum(n / 1e6, 1)} jt`;
  if (n >= 1e3) return `Rp ${fmtNum(n / 1e3, 1)} rb`;
  return `Rp ${fmtNum(n)}`;
}

export function fmtPct(n, dec = 1) {
  if (n == null || isNaN(n)) return '—';
  return `${Number(n).toFixed(dec)}%`;
}

export function budgetColor(pct) {
  if (pct > 95) return '#dc2626';
  if (pct > 80) return '#d97706';
  return '#059669';
}

export function statusClass(v) {
  if (v === 'ok') return 'ok';
  if (!v || v === 'unknown') return 'unknown';
  if (String(v).startsWith('down') || String(v).startsWith('unreachable')) return 'down';
  return 'degraded';
}
