type View = 'home' | 'results' | 'repos' | 'dashboard';

interface SidebarProps {
  currentView: View;
  onNavigate: (view: View) => void;
  repoName?: string;
  darkMode?: boolean;
  onToggleDark?: () => void;
}

export function Sidebar({ currentView, onNavigate, repoName, darkMode, onToggleDark }: SidebarProps) {
  return (
    <div
      style={{ backgroundColor: '#0d1117', minHeight: '100vh', width: '240px' }}
      className="flex flex-col py-6 px-4 flex-shrink-0"
    >
      {/* Logo */}
      <div className="mb-8">
        <span className="text-white font-bold text-lg tracking-tight">
          Repo<span style={{ color: '#2ea44f' }}>Intel</span>
        </span>
        <p style={{ color: '#57606a', fontSize: '11px' }} className="mt-1">
          Open Source Intelligence
        </p>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1">
        <NavItem
          label="Analyze Repo"
          icon="🔍"
          active={currentView === 'home'}
          onClick={() => onNavigate('home')}
        />
        {repoName && (
          <NavItem
            label={repoName}
            icon="📁"
            active={currentView === 'results'}
            onClick={() => onNavigate('results')}
            sub
          />
        )}
        <NavItem
          label="Recent Repos"
          icon="🕐"
          active={currentView === 'repos'}
          onClick={() => onNavigate('repos')}
        />
        <NavItem
          label="Analytics"
          icon="📊"
          active={currentView === 'dashboard'}
          onClick={() => onNavigate('dashboard')}
        />
      </nav>


      {/* Footer */}
      <div className="mt-auto flex flex-col gap-2">
        <button
          onClick={onToggleDark}
          className="text-xs px-3 py-2 rounded text-left flex items-center gap-2"
          style={{ color: '#8b949e' }}
        >
          {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
        </button>
        <p style={{ color: '#57606a', fontSize: '11px' }}>
          Repo Intel v1.0
        </p>
      </div>
    </div>
  );
}

function NavItem({
  label, icon, active, onClick, sub
}: {
  label: string; icon: string; active: boolean;
  onClick: () => void; sub?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 rounded text-sm flex items-center gap-2 transition-colors"
      style={{
        backgroundColor: active ? '#21262d' : 'transparent',
        color: active ? '#ffffff' : '#8b949e',
        paddingLeft: sub ? '28px' : '12px',
        fontSize: sub ? '12px' : '13px',
      }}
    >
      <span>{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  );
}
