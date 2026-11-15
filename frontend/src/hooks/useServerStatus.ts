import { useEffect, useState } from 'react';
import { pingServer, waitForServer } from '../api/client';

export type ServerState = 'checking' | 'waking' | 'ready' | 'down';

export function useServerStatus() {
  const [state, setState] = useState<ServerState>('checking');
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (await pingServer(4000)) {
        if (!cancelled) setState('ready');
        return;
      }
      if (cancelled) return;
      setState('waking');
      const ok = await waitForServer((s) => !cancelled && setSeconds(s));
      if (!cancelled) setState(ok ? 'ready' : 'down');
    })();
    return () => { cancelled = true; };
  }, []);

  return { state, seconds };
}
