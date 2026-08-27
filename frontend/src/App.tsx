import { useState, useEffect } from 'react';
import { Layout } from './components/Layout/Layout';
import { UrlInputForm } from './components/Home/UrlInputForm';
import { RecentReposView } from './components/Home/RecentReposView';
import { ProgressView } from './components/Analysis/ProgressView';
import { ResultsDashboard } from './components/Analysis/ResultsDashboard';
import { AnalyticsDashboard } from './components/Dashboard/AnalyticsDashboard';
import { useAnalysis } from './hooks/useAnalysis';

type View = 'home' | 'results' | 'repos' | 'dashboard';

export default function App() {
  const { startAnalysis, taskStatus, loading, error } = useAnalysis();
  const [view, setView] = useState<View>('home');
  const [repoId, setRepoId] = useState<number | null>(null);
  const [repoName, setRepoName] = useState<string>('');
  const [darkMode, setDarkMode] = useState(false);
  const [userProfile, setUserProfile] = useState({
    skill_level: 'intermediate',
    available_hours_per_week: 5,
  });

  // Apply dark mode via class on <html> element (CSS variables in index.css)
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Handle analysis completion - switch to results view
  useEffect(() => {
    if (taskStatus?.status === 'completed' && taskStatus.result?.repo_id) {
      setRepoId(taskStatus.result.repo_id);
      setView('results');
    }
    // Failed: stay on home page, error will show via useAnalysis hook
  }, [taskStatus]);

  const handleSubmit = async (data: any) => {
    setUserProfile({
      skill_level: data.skill_level,
      available_hours_per_week: data.available_hours_per_week,
    });
    const urlParts = data.url.replace('https://github.com/', '');
    setRepoName(urlParts);
    await startAnalysis(data);
  };

  const showProgress = loading && view !== 'results';

  return (
    <Layout
      currentView={view}
      onNavigate={(v) => {
        if (v === 'home') {
          setView('home');
        } else if (v === 'results' && repoId) {
          setView('results');
        } else if (v === 'repos') {
          setView('repos');
        } else if (v === 'dashboard') {
          setView('dashboard');
        }
      }}
      repoName={repoName || undefined}
      darkMode={darkMode}
      onToggleDark={() => setDarkMode(!darkMode)}
    >
      {view === 'home' && !showProgress && (
        <UrlInputForm
          onSubmit={handleSubmit}
          loading={loading}
          error={error}
        />
      )}

      {showProgress && (
        <ProgressView taskStatus={taskStatus} />
      )}

      {view === 'results' && repoId && (
        <ResultsDashboard repoId={repoId} userProfile={userProfile} />
      )}

      {view === 'repos' && (
        <RecentReposView />
      )}

      {view === 'dashboard' && (
        <AnalyticsDashboard />
      )}
    </Layout>
  );
}