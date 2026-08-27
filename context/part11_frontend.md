# CONTEXT FILE: Part 11 - React Frontend
# Project: RepoInsight
# Style: Clean Developer Tool (dark sidebar, white content, GitHub-inspired)
# Read the existing codebase before writing any code.
# Do not add anything not specified here.

---

## What Was Built in Parts 1-10

Backend API endpoints available:
- POST /api/repos/analyze          → trigger analysis, returns task_id
- GET  /api/repos/analyze/status/{task_id} → poll status
- GET  /api/repos/{repo_id}        → repo metadata
- GET  /api/repos/{repo_id}/analysis → full analysis text
- GET  /api/repos/{repo_id}/opportunities → scored opportunities
- POST /api/repos/{repo_id}/opportunities/match → matched for user
- GET  /api/repos                  → list analyzed repos
- GET  /api/admin/quota            → API quota status

Frontend already has:
- React 18 + TypeScript + Vite + Tailwind CSS
- Basic App.tsx placeholder
- Vite proxy: /api → http://localhost:8000

---

## What Part 11 Builds

Complete frontend UI with these pages/views:
1. Home page (URL input)
2. Analysis progress page (polling)
3. Results dashboard (summary + tabs)
4. Opportunities list (with filters + matching)

Style: Dark sidebar, white/light content area, monospace for code,
GitHub-inspired, minimal color palette.

Color palette:
- Sidebar bg: #0d1117 (GitHub dark)
- Content bg: #ffffff
- Border: #e1e4e8
- Primary accent: #2ea44f (GitHub green)
- Text primary: #24292f
- Text muted: #57606a
- Code bg: #f6f8fa
- Beginner badge: #2ea44f (green)
- Intermediate badge: #fb8500 (orange)
- Advanced badge: #e03e2d (red)

---

## File Structure to Create

frontend/src/
├── api/
│   └── client.ts              # Axios API client
├── components/
│   ├── Layout/
│   │   ├── Sidebar.tsx        # Dark sidebar with nav
│   │   └── Layout.tsx         # Sidebar + content wrapper
│   ├── Home/
│   │   └── UrlInputForm.tsx   # Repo URL input + skill selector
│   ├── Analysis/
│   │   ├── ProgressView.tsx   # Polling + step display
│   │   └── ResultsDashboard.tsx # Tabbed results view
│   ├── Opportunities/
│   │   ├── OpportunityCard.tsx
│   │   ├── OpportunityList.tsx
│   │   └── DifficultyBadge.tsx
│   └── shared/
│       ├── LoadingSpinner.tsx
│       └── ErrorMessage.tsx
├── hooks/
│   └── useAnalysis.ts         # Polling logic hook
├── types/
│   └── index.ts               # TypeScript types
├── App.tsx                    # Updated with routing
├── main.tsx                   # Unchanged
└── index.css                  # Unchanged

---

## TypeScript Types

### frontend/src/types/index.ts

```typescript
export interface AnalysisRequest {
  url: string;
  skill_level: string;
  available_hours_per_week: number;
  preferred_categories: string[];
}

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'started' | 'processing' | 'completed' | 'failed' | 'queued';
  step?: string;
  result?: AnalysisResult;
  error?: string;
}

export interface AnalysisResult {
  status: string;
  analysis_id: number;
  quality_tier: string;
  opportunities_found: number;
}

export interface Analysis {
  id: number;
  repo_id: number;
  quality_tier: string;
  summary: string;
  architecture_explanation: string;
  code_walkthrough: string;
  common_patterns: string;
  gotchas_and_tips: string;
  setup_guide: string;
  tech_stack: Record<string, any>;
  directory_structure: Record<string, any>;
  open_issues: any[];
  contributors: any[];
  commits: any[];
  code_quality_metrics: Record<string, any>;
  created_at: string;
}

export interface Repository {
  id: number;
  owner: string;
  name: string;
  full_name: string;
  url: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  open_issues_count: number;
  analysis_status: string;
  last_analyzed_at: string;
}

export interface Opportunity {
  id: number;
  title: string;
  description: string;
  category: string;
  difficulty: number;
  impact: number;
  learning_value: number;
  overall_score: number;
  estimated_hours: number;
  difficulty_tier: 'beginner' | 'intermediate' | 'advanced';
  github_issue_number?: number;
  github_issue_url?: string;
  suitability_score?: number;
  match_percentage?: number;
  recommended?: boolean;
}

export interface UserProfile {
  skill_level: string;
  available_hours_per_week: number;
  preferred_categories: string[];
}
```

---

## API Client

### frontend/src/api/client.ts

```typescript
import axios from 'axios';
import type {
  AnalysisRequest, TaskStatus, Analysis,
  Repository, Opportunity, UserProfile
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export const triggerAnalysis = async (data: AnalysisRequest) => {
  const res = await api.post('/repos/analyze', data);
  return res.data as { task_id: string; status: string; message: string };
};

export const getTaskStatus = async (taskId: string) => {
  const res = await api.get(`/repos/analyze/status/${taskId}`);
  return res.data as TaskStatus;
};

export const getRepository = async (repoId: number) => {
  const res = await api.get(`/repos/${repoId}`);
  return res.data as Repository;
};

export const getAnalysis = async (repoId: number) => {
  const res = await api.get(`/repos/${repoId}/analysis`);
  return res.data as Analysis;
};

export const getOpportunities = async (repoId: number, tier?: string) => {
  const params = tier ? { difficulty_tier: tier } : {};
  const res = await api.get(`/repos/${repoId}/opportunities`, { params });
  return res.data as { total: number; opportunities: Opportunity[] };
};

export const getMatchedOpportunities = async (
  repoId: number,
  profile: UserProfile
) => {
  const res = await api.post(`/repos/${repoId}/opportunities/match`, profile);
  return res.data;
};

export const listRepos = async () => {
  const res = await api.get('/repos');
  return res.data as { total: number; repositories: Repository[] };
};

export const getQuota = async () => {
  const res = await api.get('/admin/quota');
  return res.data;
};
```

---

## Custom Hook

### frontend/src/hooks/useAnalysis.ts

```typescript
import { useState, useEffect, useRef } from 'react';
import { triggerAnalysis, getTaskStatus } from '../api/client';
import type { AnalysisRequest, TaskStatus } from '../types';

export function useAnalysis() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startAnalysis = async (data: AnalysisRequest) => {
    setLoading(true);
    setError(null);
    setTaskStatus(null);
    try {
      const res = await triggerAnalysis(data);
      setTaskId(res.task_id);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to start analysis');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId);
        setTaskStatus(status);

        if (status.status === 'completed' || status.status === 'failed') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setLoading(false);
        }
      } catch (e) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setError('Failed to get analysis status');
        setLoading(false);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId]);

  return { startAnalysis, taskStatus, loading, error, taskId };
}
```

---

## Shared Components

### frontend/src/components/shared/LoadingSpinner.tsx

```tsx
export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return (
    <div className={`${sizes[size]} border-2 border-gray-200 border-t-green-500 rounded-full animate-spin`} />
  );
}
```

### frontend/src/components/shared/ErrorMessage.tsx

```tsx
export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
      {message}
    </div>
  );
}
```

---

## Layout Components

### frontend/src/components/Layout/Sidebar.tsx

```tsx
type View = 'home' | 'results' | 'repos';

interface SidebarProps {
  currentView: View;
  onNavigate: (view: View) => void;
  repoName?: string;
}

export function Sidebar({ currentView, onNavigate, repoName }: SidebarProps) {
  return (
    <div
      style={{ backgroundColor: '#0d1117', minHeight: '100vh', width: '240px' }}
      className="flex flex-col py-6 px-4 flex-shrink-0"
    >
      {/* Logo */}
      <div className="mb-8">
        <span className="text-white font-bold text-lg tracking-tight">
          Repo<span style={{ color: '#2ea44f' }}>Insight</span>
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
      </nav>

      {/* Footer */}
      <div className="mt-auto">
        <p style={{ color: '#57606a', fontSize: '11px' }}>
          RepoInsight v1.0
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
```

### frontend/src/components/Layout/Layout.tsx

```tsx
import { Sidebar } from './Sidebar';

type View = 'home' | 'results' | 'repos';

interface LayoutProps {
  children: React.ReactNode;
  currentView: View;
  onNavigate: (view: View) => void;
  repoName?: string;
}

export function Layout({ children, currentView, onNavigate, repoName }: LayoutProps) {
  return (
    <div className="flex" style={{ minHeight: '100vh' }}>
      <Sidebar
        currentView={currentView}
        onNavigate={onNavigate}
        repoName={repoName}
      />
      <main
        className="flex-1 overflow-auto"
        style={{ backgroundColor: '#f6f8fa' }}
      >
        {children}
      </main>
    </div>
  );
}
```

---

## Home Page

### frontend/src/components/Home/UrlInputForm.tsx

```tsx
import { useState } from 'react';
import type { AnalysisRequest } from '../../types';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';

interface Props {
  onSubmit: (data: AnalysisRequest) => void;
  loading: boolean;
  error: string | null;
}

export function UrlInputForm({ onSubmit, loading, error }: Props) {
  const [url, setUrl] = useState('');
  const [skillLevel, setSkillLevel] = useState('intermediate');
  const [hoursPerWeek, setHoursPerWeek] = useState(5);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit({
      url: url.trim(),
      skill_level: skillLevel,
      available_hours_per_week: hoursPerWeek,
      preferred_categories: [],
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      {/* Header */}
      <div className="mb-10">
        <h1
          className="text-3xl font-bold mb-2"
          style={{ color: '#24292f', fontFamily: 'monospace' }}
        >
          Analyze any GitHub repository
        </h1>
        <p style={{ color: '#57606a' }}>
          Get AI-powered insights, architecture explanation, and personalized
          contribution opportunities.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* URL Input */}
        <div>
          <label
            className="block text-sm font-medium mb-1"
            style={{ color: '#24292f' }}
          >
            GitHub Repository URL
          </label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            className="w-full px-3 py-2 rounded border text-sm outline-none"
            style={{
              borderColor: '#d0d7de',
              fontFamily: 'monospace',
              color: '#24292f',
            }}
            disabled={loading}
          />
        </div>

        {/* Skill Level */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: '#24292f' }}
            >
              Your Skill Level
            </label>
            <select
              value={skillLevel}
              onChange={(e) => setSkillLevel(e.target.value)}
              className="w-full px-3 py-2 rounded border text-sm outline-none"
              style={{ borderColor: '#d0d7de', color: '#24292f' }}
              disabled={loading}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div className="flex-1">
            <label
              className="block text-sm font-medium mb-1"
              style={{ color: '#24292f' }}
            >
              Hours / Week Available
            </label>
            <input
              type="number"
              value={hoursPerWeek}
              onChange={(e) => setHoursPerWeek(Number(e.target.value))}
              min={1}
              max={40}
              className="w-full px-3 py-2 rounded border text-sm outline-none"
              style={{ borderColor: '#d0d7de', color: '#24292f' }}
              disabled={loading}
            />
          </div>
        </div>

        {error && <ErrorMessage message={error} />}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium text-white transition-opacity"
          style={{
            backgroundColor: '#2ea44f',
            opacity: loading || !url.trim() ? 0.6 : 1,
          }}
        >
          {loading ? <LoadingSpinner size="sm" /> : null}
          {loading ? 'Analyzing...' : 'Analyze Repository'}
        </button>
      </form>

      {/* Example repos */}
      <div className="mt-8">
        <p className="text-xs mb-2" style={{ color: '#57606a' }}>
          Try with:
        </p>
        <div className="flex flex-wrap gap-2">
          {[
            'https://github.com/psf/requests',
            'https://github.com/pallets/flask',
            'https://github.com/encode/django-rest-framework',
          ].map((example) => (
            <button
              key={example}
              onClick={() => setUrl(example)}
              className="text-xs px-2 py-1 rounded border"
              style={{
                borderColor: '#d0d7de',
                color: '#57606a',
                fontFamily: 'monospace',
              }}
              disabled={loading}
            >
              {example.replace('https://github.com/', '')}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Analysis Progress

### frontend/src/components/Analysis/ProgressView.tsx

```tsx
import { LoadingSpinner } from '../shared/LoadingSpinner';
import type { TaskStatus } from '../../types';

const STEPS = [
  'Fetching GitHub data',
  'Analyzing repository',
  'Selecting AI tier',
  'Running AI analysis',
  'Scoring opportunities',
  'Saving to database',
];

interface Props {
  taskStatus: TaskStatus | null;
}

export function ProgressView({ taskStatus }: Props) {
  const currentStep = taskStatus?.step || 'Starting...';
  const currentIndex = STEPS.findIndex((s) =>
    currentStep.toLowerCase().includes(s.toLowerCase().split(' ')[0])
  );

  return (
    <div className="max-w-xl mx-auto px-6 py-16">
      <div
        className="bg-white rounded border p-8"
        style={{ borderColor: '#e1e4e8' }}
      >
        <div className="flex items-center gap-3 mb-6">
          <LoadingSpinner size="md" />
          <div>
            <p className="font-medium" style={{ color: '#24292f' }}>
              Analyzing repository...
            </p>
            <p className="text-sm" style={{ color: '#57606a' }}>
              This takes 2-3 minutes
            </p>
          </div>
        </div>

        {/* Steps */}
        <div className="flex flex-col gap-2">
          {STEPS.map((step, i) => {
            const done = i < currentIndex;
            const active = i === currentIndex;
            return (
              <div key={step} className="flex items-center gap-3">
                <span className="text-sm">
                  {done ? '✅' : active ? '⏳' : '⬜'}
                </span>
                <span
                  className="text-sm"
                  style={{
                    color: done ? '#2ea44f' : active ? '#24292f' : '#8b949e',
                    fontWeight: active ? '500' : 'normal',
                  }}
                >
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

---

## Opportunity Components

### frontend/src/components/Opportunities/DifficultyBadge.tsx

```tsx
const COLORS = {
  beginner: { bg: '#dafbe1', text: '#2ea44f', border: '#9be9a8' },
  intermediate: { bg: '#fff3e0', text: '#fb8500', border: '#ffcc80' },
  advanced: { bg: '#ffeef0', text: '#e03e2d', border: '#ffc1c0' },
};

export function DifficultyBadge({
  tier,
}: {
  tier: 'beginner' | 'intermediate' | 'advanced';
}) {
  const color = COLORS[tier] || COLORS.intermediate;
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full border font-medium capitalize"
      style={{
        backgroundColor: color.bg,
        color: color.text,
        borderColor: color.border,
      }}
    >
      {tier}
    </span>
  );
}
```

### frontend/src/components/Opportunities/OpportunityCard.tsx

```tsx
import { DifficultyBadge } from './DifficultyBadge';
import type { Opportunity } from '../../types';

export function OpportunityCard({ opp }: { opp: Opportunity }) {
  return (
    <div
      className="bg-white rounded border p-4 hover:shadow-sm transition-shadow"
      style={{ borderColor: '#e1e4e8' }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm font-medium" style={{ color: '#24292f' }}>
          {opp.title}
        </p>
        <DifficultyBadge tier={opp.difficulty_tier} />
      </div>

      {/* Description */}
      {opp.description && (
        <p className="text-xs mb-3" style={{ color: '#57606a' }}>
          {opp.description.slice(0, 120)}
          {opp.description.length > 120 ? '...' : ''}
        </p>
      )}

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: '#57606a' }}>
        <span>⏱ {opp.estimated_hours}h</span>
        <span>📚 Learning: {opp.learning_value}/10</span>
        <span>💥 Impact: {opp.impact}/10</span>
        {opp.match_percentage !== undefined && (
          <span
            className="font-medium"
            style={{ color: opp.recommended ? '#2ea44f' : '#e03e2d' }}
          >
            {opp.match_percentage}% match
          </span>
        )}
        {opp.github_issue_url && (
          <a
            href={opp.github_issue_url}
            target="_blank"
            rel="noreferrer"
            className="underline"
            style={{ color: '#0969da' }}
          >
            #{opp.github_issue_number}
          </a>
        )}
      </div>
    </div>
  );
}
```

### frontend/src/components/Opportunities/OpportunityList.tsx

```tsx
import { useState } from 'react';
import { OpportunityCard } from './OpportunityCard';
import type { Opportunity } from '../../types';

interface Props {
  opportunities: Opportunity[];
  showFilter?: boolean;
}

const TIERS = ['all', 'beginner', 'intermediate', 'advanced'];

export function OpportunityList({ opportunities, showFilter = true }: Props) {
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all'
    ? opportunities
    : opportunities.filter((o) => o.difficulty_tier === filter);

  return (
    <div>
      {showFilter && (
        <div className="flex gap-2 mb-4">
          {TIERS.map((tier) => (
            <button
              key={tier}
              onClick={() => setFilter(tier)}
              className="text-xs px-3 py-1 rounded border capitalize transition-colors"
              style={{
                backgroundColor: filter === tier ? '#24292f' : 'white',
                color: filter === tier ? 'white' : '#57606a',
                borderColor: filter === tier ? '#24292f' : '#d0d7de',
              }}
            >
              {tier}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-3">
        {filtered.length === 0 ? (
          <p className="text-sm" style={{ color: '#57606a' }}>
            No opportunities found for this filter.
          </p>
        ) : (
          filtered.map((opp, i) => <OpportunityCard key={opp.id || i} opp={opp} />)
        )}
      </div>
    </div>
  );
}
```

---

## Results Dashboard

### frontend/src/components/Analysis/ResultsDashboard.tsx

```tsx
import { useState, useEffect } from 'react';
import { getAnalysis, getOpportunities, getMatchedOpportunities } from '../../api/client';
import { OpportunityList } from '../Opportunities/OpportunityList';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';
import type { Analysis, Opportunity } from '../../types';

const TABS = ['Summary', 'Architecture', 'Setup Guide', 'Opportunities', 'Matched'];

interface Props {
  repoId: number;
  userProfile: { skill_level: string; available_hours_per_week: number };
}

export function ResultsDashboard({ repoId, userProfile }: Props) {
  const [tab, setTab] = useState('Summary');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [matched, setMatched] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [analysisData, oppsData] = await Promise.all([
          getAnalysis(repoId),
          getOpportunities(repoId),
        ]);
        setAnalysis(analysisData);
        setOpportunities(oppsData.opportunities);

        const matchedData = await getMatchedOpportunities(repoId, {
          skill_level: userProfile.skill_level,
          available_hours_per_week: userProfile.available_hours_per_week,
          preferred_categories: [],
        });
        setMatched(matchedData.top_matches || []);
      } catch (e: any) {
        setError('Failed to load analysis results');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !analysis) {
    return <ErrorMessage message={error || 'No analysis found'} />;
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Quality badge */}
      <div className="flex items-center gap-2 mb-6">
        <span
          className="text-xs px-2 py-1 rounded border font-medium"
          style={{
            backgroundColor: analysis.quality_tier === 'HIGH' ? '#dafbe1' : '#fff3e0',
            color: analysis.quality_tier === 'HIGH' ? '#2ea44f' : '#fb8500',
            borderColor: analysis.quality_tier === 'HIGH' ? '#9be9a8' : '#ffcc80',
          }}
        >
          {analysis.quality_tier} Quality Analysis
        </span>
        <span className="text-xs" style={{ color: '#57606a' }}>
          {opportunities.length} opportunities found
        </span>
      </div>

      {/* Tabs */}
      <div
        className="flex border-b mb-6"
        style={{ borderColor: '#e1e4e8' }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-2 text-sm border-b-2 transition-colors"
            style={{
              borderBottomColor: tab === t ? '#2ea44f' : 'transparent',
              color: tab === t ? '#24292f' : '#57606a',
              fontWeight: tab === t ? '500' : 'normal',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {tab === 'Summary' && (
          <Section title="Project Summary" content={analysis.summary} />
        )}
        {tab === 'Architecture' && (
          <>
            <Section title="Architecture" content={analysis.architecture_explanation} />
            <Section title="Code Walkthrough" content={analysis.code_walkthrough} />
            <Section title="Common Patterns" content={analysis.common_patterns} />
            <Section title="Gotchas & Tips" content={analysis.gotchas_and_tips} />
          </>
        )}
        {tab === 'Setup Guide' && (
          <Section title="Setup Guide" content={analysis.setup_guide} code />
        )}
        {tab === 'Opportunities' && (
          <OpportunityList opportunities={opportunities} showFilter />
        )}
        {tab === 'Matched' && (
          <>
            <p className="text-sm mb-4" style={{ color: '#57606a' }}>
              Ranked by match for a{' '}
              <strong>{userProfile.skill_level}</strong> developer with{' '}
              <strong>{userProfile.available_hours_per_week}h/week</strong>.
            </p>
            <OpportunityList opportunities={matched} showFilter={false} />
          </>
        )}
      </div>
    </div>
  );
}

function Section({
  title, content, code
}: {
  title: string; content: string; code?: boolean;
}) {
  if (!content) return null;
  return (
    <div className="mb-8">
      <h2
        className="text-base font-semibold mb-3"
        style={{ color: '#24292f' }}
      >
        {title}
      </h2>
      <div
        className="text-sm leading-relaxed rounded p-4"
        style={{
          backgroundColor: code ? '#f6f8fa' : 'white',
          color: '#24292f',
          border: '1px solid #e1e4e8',
          fontFamily: code ? 'monospace' : 'inherit',
          whiteSpace: code ? 'pre-wrap' : 'normal',
        }}
      >
        {content}
      </div>
    </div>
  );
}
```

---

## Updated App.tsx

### frontend/src/App.tsx

```tsx
import { useState } from 'react';
import { Layout } from './components/Layout/Layout';
import { UrlInputForm } from './components/Home/UrlInputForm';
import { ProgressView } from './components/Analysis/ProgressView';
import { ResultsDashboard } from './components/Analysis/ResultsDashboard';
import { useAnalysis } from './hooks/useAnalysis';

type View = 'home' | 'results' | 'repos';

export default function App() {
  const { startAnalysis, taskStatus, loading, error } = useAnalysis();
  const [view, setView] = useState<View>('home');
  const [repoId, setRepoId] = useState<number | null>(null);
  const [repoName, setRepoName] = useState<string>('');
  const [userProfile, setUserProfile] = useState({
    skill_level: 'intermediate',
    available_hours_per_week: 5,
  });

  const handleSubmit = async (data: any) => {
    setUserProfile({
      skill_level: data.skill_level,
      available_hours_per_week: data.available_hours_per_week,
    });
    const urlParts = data.url.replace('https://github.com/', '');
    setRepoName(urlParts);
    await startAnalysis(data);
  };

  // When analysis completes, extract repo_id and switch to results view
  if (
    taskStatus?.status === 'completed' &&
    taskStatus.result?.analysis_id &&
    view !== 'results'
  ) {
    setRepoId(taskStatus.result.analysis_id);
    setView('results');
  }

  const showProgress = loading && view !== 'results';

  return (
    <Layout
      currentView={view}
      onNavigate={(v) => {
        if (v === 'home') setView('home');
        else setView(v);
      }}
      repoName={repoName || undefined}
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
    </Layout>
  );
}
```

---

## Validation Checklist

[ ] All files created in correct paths
[ ] npm install runs without errors: cd frontend && npm install
[ ] npm run dev starts without errors: npm run dev
[ ] Frontend loads at http://localhost:5173
[ ] Dark sidebar visible on left
[ ] URL input form visible on right
[ ] Example repo buttons populate the URL field
[ ] Skill level dropdown and hours input work
[ ] Analyze button triggers analysis (check Network tab → POST /api/repos/analyze)
[ ] Progress view shows steps while polling
[ ] On completion, results dashboard loads with tabs
[ ] Summary tab shows AI-generated text
[ ] Opportunities tab shows scored list with difficulty badges
[ ] Matched tab shows ranked opportunities with match percentages
[ ] Filter buttons (all/beginner/intermediate/advanced) work on opportunities tab
[ ] No TypeScript errors: npm run build

---

## What Part 12 Will Cover

PDF generation:
- Weasyprint setup
- HTML templates for 4 PDF types
- POST /api/pdfs/generate endpoint
- Download button in frontend

Do NOT add PDF in Part 11.
