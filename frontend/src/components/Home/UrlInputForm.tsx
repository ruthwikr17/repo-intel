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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onSubmit({
      url: url.trim(),
      skill_level: 'intermediate',
      available_hours_per_week: 10,
      preferred_categories: [],
    });
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <div className="mb-10">
        <h1
          className="text-3xl font-bold mb-2"
          style={{ color: '#24292f', fontFamily: 'monospace' }}
        >
          Analyze any GitHub repository
        </h1>
        <p style={{ color: '#57606a' }}>
          Get AI-powered insights, architecture explanation,
          and contribution opportunities — instantly.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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

        {error && <ErrorMessage message={error} />}

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

      <div className="mt-8">
        <p className="text-xs mb-2" style={{ color: '#57606a' }}>
          Try with a popular repo:
        </p>
        <div className="flex flex-wrap gap-2">
          {[
            'https://github.com/psf/requests',
            'https://github.com/pallets/flask',
            'https://github.com/django/django',
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
