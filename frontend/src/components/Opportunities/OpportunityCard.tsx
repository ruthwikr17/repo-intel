import { useState } from 'react';
import { DifficultyBadge } from './DifficultyBadge';
import { OpportunityDetail } from './OpportunityDetail';
import type { Opportunity } from '../../types';

interface Props {
  opp: Opportunity;
  repoId: number;
}

export function OpportunityCard({ opp, repoId }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div
        className="bg-white rounded border p-4 cursor-pointer transition-all"
        style={{ borderColor: '#e1e4e8' }}
        onClick={() => setOpen(true)}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
          (e.currentTarget as HTMLDivElement).style.borderColor = '#2ea44f';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
          (e.currentTarget as HTMLDivElement).style.borderColor = '#e1e4e8';
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <p className="text-sm font-medium" style={{ color: '#24292f' }}>
            {opp.title}
          </p>
          <DifficultyBadge tier={opp.difficulty_tier} />
        </div>

        {/* Description preview */}
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
            <span style={{ color: '#0969da' }}>
              #{opp.github_issue_number}
            </span>
          )}
        </div>

        {/* Click hint */}
        <p
          className="text-xs mt-2"
          style={{ color: '#8b949e' }}
        >
          Click to view details →
        </p>
      </div>

      {open && (
        <OpportunityDetail opp={opp} repoId={repoId} onClose={() => setOpen(false)} />
      )}
    </>
  );
}