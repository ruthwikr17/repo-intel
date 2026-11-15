import { Sidebar } from './Sidebar';
import { ServerStatusBanner } from '../shared/ServerStatusBanner';
import { useServerStatus } from '../../hooks/useServerStatus';

type View = 'home' | 'results' | 'repos' | 'dashboard';

interface LayoutProps {
  children: React.ReactNode;
  currentView: View;
  onNavigate: (view: View) => void;
  repoName?: string;
  darkMode?: boolean;
  onToggleDark?: () => void;
}

export function Layout({ children, currentView, onNavigate, repoName, darkMode, onToggleDark }: LayoutProps) {
  const { state: serverState, seconds: serverSeconds } = useServerStatus();

  return (
    <div className="flex" style={{ minHeight: '100vh' }}>
      <Sidebar
        currentView={currentView}
        onNavigate={onNavigate}
        repoName={repoName}
        darkMode={darkMode}
        onToggleDark={onToggleDark}
      />
      <main
        className="flex-1 overflow-auto"
        style={{ backgroundColor: darkMode ? '#0d1117' : '#f6f8fa' }}
      >
        <ServerStatusBanner state={serverState} seconds={serverSeconds} />
        {children}
      </main>
    </div>
  );
}
