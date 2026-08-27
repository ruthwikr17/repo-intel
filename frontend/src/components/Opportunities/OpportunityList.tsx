import { useState } from 'react';
import { OpportunityCard } from './OpportunityCard';
import type { Opportunity } from '../../types';

interface Props {
  opportunities: Opportunity[];
  showFilter?: boolean;
  repoId: number;
}

const TIERS = ['all', 'beginner', 'intermediate', 'advanced'];

export function OpportunityList({ opportunities, showFilter = true, repoId }: Props) {
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
          filtered.map((opp, i) => <OpportunityCard key={opp.id || i} opp={opp} repoId={repoId} />)
        )}
      </div>
    </div>
  );
}

