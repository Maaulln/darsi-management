import { useState, useEffect, useCallback } from 'react';

export async function apiFetch(path) {
  const r = await fetch(path);
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${r.status}`);
  }
  return r.json();
}

export async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${r.status}`);
  }
  return r.json();
}

export function useApi(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiFetch(path)
      .then(d => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [path]);

  useEffect(() => load(), [load]);

  return { data, loading, error, refetch: load };
}
