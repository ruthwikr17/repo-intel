import { DifficultyBadge } from './DifficultyBadge';
import { AIHelperButtons } from './AIHelperButtons';
import type { Opportunity } from '../../types';

interface Props {
  opp: Opportunity;
  repoId: number;
  onClose: () => void;
}

export function OpportunityDetail({ opp, repoId, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-screen overflow-y-auto"
        style={{ border: '1px solid #e1e4e8' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between p-5"
          style={{ borderBottom: '1px solid #e1e4e8' }}
        >
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <DifficultyBadge tier={opp.difficulty_tier} />
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: '#f6f8fa', color: '#57606a' }}
              >
                {opp.category}
              </span>
            </div>
            <h2
              className="text-base font-semibold"
              style={{ color: '#24292f' }}
            >
              {opp.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-xl font-light"
            style={{ color: '#57606a' }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col gap-5">

          {/* Match score if available */}
          {opp.match_percentage !== undefined && (
            <div
              className="rounded p-3 flex items-center gap-3"
              style={{
                backgroundColor: opp.recommended ? '#dafbe1' : '#fff3e0',
                border: `1px solid ${opp.recommended ? '#9be9a8' : '#ffcc80'}`
              }}
            >
              <span style={{ fontSize: '20px' }}>
                {opp.recommended ? '✅' : '⚠️'}
              </span>
              <div>
                <p
                  className="text-sm font-medium"
                  style={{ color: opp.recommended ? '#2ea44f' : '#fb8500' }}
                >
                  {opp.match_percentage}% match for your profile
                </p>
                <p className="text-xs" style={{ color: '#57606a' }}>
                  {opp.recommended
                    ? 'This is a good fit for your skill level and availability.'
                    : 'This may be outside your current skill level or time constraints.'}
                </p>
              </div>
            </div>
          )}

          {/* What to do */}
          <div>
            <h3 className="text-sm font-semibold mb-2" style={{ color: '#24292f' }}>
              What to Do
            </h3>
            <p className="text-sm" style={{ color: '#24292f', lineHeight: '1.7' }}>
              {(opp as any).what_to_do || opp.description || 'No description available.'}
            </p>
          </div>

          {/* Files to look at */}
          {(opp as any).files_to_look_at?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: '#24292f' }}>
                Files to Look At
              </h3>
              <div className="flex flex-wrap gap-2">
                {(opp as any).files_to_look_at.map((f: string) => (
                  <span
                    key={f}
                    className="text-xs px-2 py-1 rounded"
                    style={{ backgroundColor: '#f6f8fa', border: '1px solid #e1e4e8',
                             fontFamily: 'monospace', color: '#24292f' }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metrics */}
          <div>
            <h3
              className="text-sm font-semibold mb-3"
              style={{ color: '#24292f' }}
            >
              Task Metrics
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Difficulty', value: `${opp.difficulty}/10` },
                { label: 'Learning Value', value: `${opp.learning_value}/10` },
                { label: 'Impact', value: `${opp.impact}/10` },
                { label: 'Estimated Time', value: `${opp.estimated_hours}h` },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="rounded p-3 text-center"
                  style={{ backgroundColor: '#f6f8fa', border: '1px solid #e1e4e8' }}
                >
                  <p
                    className="text-lg font-bold"
                    style={{ color: '#24292f' }}
                  >
                    {value}
                  </p>
                  <p className="text-xs" style={{ color: '#57606a' }}>
                    {label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Why it matters */}
          <div>
            <h3 className="text-sm font-semibold mb-2" style={{ color: '#24292f' }}>
              Why It Matters
            </h3>
            <p className="text-sm" style={{ color: '#57606a', lineHeight: '1.7' }}>
              {(opp as any).why_it_matters || 'Completing this improves the project quality.'}
            </p>
          </div>

          {/* How to get started */}
          <div>
            <h3
              className="text-sm font-semibold mb-2"
              style={{ color: '#24292f' }}
            >
              How to Get Started
            </h3>
            <div className="flex flex-col gap-2">
              {[
                '1. Fork the repository and clone your fork locally',
                '2. Create a new branch: git checkout -b your-branch-name',
                '3. Make your changes following the project\'s code style',
                '4. Run the test suite to ensure nothing is broken',
                '5. Commit with a clear message and open a Pull Request',
              ].map((step) => (
                <p
                  key={step}
                  className="text-sm"
                  style={{ color: '#24292f', lineHeight: '1.6' }}
                >
                  {step}
                </p>
              ))}
            </div>
          </div>

          {/* AI Help Section */}
          <div
            className="rounded-lg p-4"
            style={{ backgroundColor: '#f6f8fa', border: '1px solid #e1e4e8' }}
          >
            <AIHelperButtons
              repoId={repoId}
              opportunityId={opp.id}
              opportunityTitle={opp.title}
            />
          </div>


          {/* GitHub Issue Link */}
          {opp.github_issue_url && (
            <div>
              <h3
                className="text-sm font-semibold mb-2"
                style={{ color: '#24292f' }}
              >
                GitHub Issue
              </h3>
              <a
                href={opp.github_issue_url}
                target="_blank"
                rel="noreferrer"
                className="text-sm underline"
                style={{ color: '#0969da' }}
              >
                #{opp.github_issue_number} — View on GitHub →
              </a>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="flex justify-end p-4 gap-2"
          style={{ borderTop: '1px solid #e1e4e8' }}
        >
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded border"
            style={{ borderColor: '#d0d7de', color: '#57606a' }}
          >
            Close
          </button>
          {opp.github_issue_url && (
            <a
              href={opp.github_issue_url}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 text-sm rounded text-white"
              style={{ backgroundColor: '#2ea44f' }}
            >
              View Issue on GitHub
            </a>
          )}
        </div>
      </div>
    </div>
  );
}