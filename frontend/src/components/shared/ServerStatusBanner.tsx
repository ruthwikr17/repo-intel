import type { ServerState } from '../../hooks/useServerStatus';

export function ServerStatusBanner({ state, seconds }: { state: ServerState; seconds: number }) {
  if (state === 'ready' || state === 'checking') return null;

  const isDown = state === 'down';
  return (
    <div
      style={{
        padding: '10px 16px',
        fontSize: '13px',
        backgroundColor: isDown ? '#ffeef0' : '#fff8e1',
        color: isDown ? '#b42318' : '#8a6d00',
        borderBottom: '1px solid var(--border)',
      }}
    >
      {isDown
        ? 'The server is not responding. It runs on free hosting - please try again in a minute.'
        : `Server is waking up (free hosting, up to ~90 seconds)... ${seconds}s`}
    </div>
  );
}
