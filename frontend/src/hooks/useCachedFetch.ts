import { useCallback, useEffect, useRef, useState } from 'react';

export function useCachedFetch<T>(key: string, fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [slow, setSlow] = useState(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSlow(false);
    const slowTimer = setTimeout(() => setSlow(true), 4000);
    try {
      const fresh = await fetcherRef.current();
      setData(fresh);
      try { localStorage.setItem(key, JSON.stringify(fresh)); } catch { /* ignore quota */ }
    } catch {
      setError('Could not reach the server.');
    } finally {
      clearTimeout(slowTimer);
      setLoading(false);
      setSlow(false);
    }
  }, [key]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, slow, reload: load };
}
