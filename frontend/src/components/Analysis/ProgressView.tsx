import { LoadingSpinner } from '../shared/LoadingSpinner';
import type { TaskStatus } from '../../types';

const STEPS = [
  'Fetching GitHub data',
  'Analyzing repository',
  'Selecting AI tier',
  'Running AI analysis',
  'Generating contribution ideas',
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
    <div className="max-w-xl mx-auto px-6 py-20">
      <div className="text-center mb-10">
        <div className="mb-6 flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
        <h1
          className="text-2xl font-bold mb-2"
          style={{ color: '#24292f', fontFamily: 'monospace' }}
        >
          Analyzing Repository
        </h1>
        <p style={{ color: '#57606a' }}>
          This typically takes 2-3 minutes. We're extracting code structure,
          running AI analysis, and finding the best contribution opportunities.
        </p>
      </div>

      {/* Progress Steps */}
      <div
        className="bg-white rounded border p-6"
        style={{ borderColor: '#e1e4e8' }}
      >
        <div className="flex flex-col gap-3">
          {STEPS.map((step, i) => {
            const done = i < currentIndex;
            const active = i === currentIndex;
            return (
              <div
                key={step}
                className="flex items-center gap-3 p-2 rounded"
                style={{
                  backgroundColor: active ? '#f6f8fa' : 'transparent',
                }}
              >
                <span className="text-sm">
                  {done ? (
                    <span style={{ color: '#2ea44f' }}>✓</span>
                  ) : active ? (
                    <span className="animate-pulse" style={{ color: '#2ea44f' }}>
                      ●
                    </span>
                  ) : (
                    <span style={{ color: '#d0d7de' }}>○</span>
                  )}
                </span>
                <span
                  className="text-sm"
                  style={{
                    color: done ? '#24292f' : active ? '#24292f' : '#8b949e',
                    fontWeight: active ? '600' : 'normal',
                  }}
                >
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tip */}
      <div className="mt-6 text-center">
        <p className="text-xs" style={{ color: '#8b949e' }}>
          💡 Tip: First-time analysis takes longer as we clone the repository.
        </p>
      </div>
    </div>
  );
}
