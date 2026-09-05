import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { getAnalysis, getOpportunities } from '../../api/client';
import { OpportunityList } from '../Opportunities/OpportunityList';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { ErrorMessage } from '../shared/ErrorMessage';
import type { Analysis, Opportunity } from '../../types';

const TABS = ['Summary', 'Architecture', 'Setup Guide', 'Opportunities'];

interface Props {
  repoId: number;
  userProfile: { skill_level: string; available_hours_per_week: number };
}

export function ResultsDashboard({ repoId, userProfile }: Props) {
  const [tab, setTab] = useState('Summary');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const handleDownloadPdf = async (reportType: string) => {
    setDownloading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_URL
        ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api`
        : '/api';
      const res = await fetch(`${baseUrl}/pdfs/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: repoId, report_type: reportType }),
      });
      const data = await res.json();
      if (data.download_url) {
        const fullUrl = data.download_url.startsWith('http')
          ? data.download_url
          : import.meta.env.VITE_API_URL
          ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}${data.download_url}`
          : data.download_url;
        window.open(fullUrl, '_blank');
      }
    } catch (e) {
      console.error('PDF download failed', e);
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    const load = async () => {
      try {
        const [analysisData, oppsData] = await Promise.all([
          getAnalysis(repoId),
          getOpportunities(repoId),
        ]);
        setAnalysis(analysisData);
        setOpportunities(oppsData.opportunities);
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

      {/* Download bar */}
      <div className="flex gap-2 mb-4">
        <span className="text-sm mr-2" style={{ color: '#57606a' }}>
          Download PDF:
        </span>
        {[
          { label: '📋 Contributor Guide', type: 'contributor_guide' },
          { label: '📊 Code Quality', type: 'code_quality' },
          { label: '📄 Executive Summary', type: 'executive_summary' },
          { label: '📁 Full Analysis', type: 'full_analysis' },
        ].map(({ label, type }) => (
          <button
            key={type}
            onClick={() => handleDownloadPdf(type)}
            disabled={downloading}
            className="text-xs px-3 py-1.5 rounded border"
            style={{
              borderColor: '#d0d7de',
              color: 'var(--text-muted)',
              backgroundColor: 'var(--bg-card)',
              opacity: downloading ? 0.6 : 1,
            }}
          >
            {downloading ? '⏳' : label}
          </button>
        ))}
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
          <Section title="Project Summary" content={analysis.summary} markdown />
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
          <Section title="Setup Guide" content={analysis.setup_guide} markdown />
        )}
        {tab === 'Opportunities' && (
          <OpportunityList opportunities={opportunities} showFilter repoId={repoId} />
        )}

      </div>
    </div>
  );
}

function Section({
  title,
  content,
  code = false,
  markdown = false,
}: {
  title: string;
  content: string;
  code?: boolean;
  markdown?: boolean;
}) {

  if (!content) return null;

  // Check if content contains Gemini error message
  const hasError = content.includes('[Gemini Error') || content.includes('Error:');

  return (
    <div className="mb-8">
      <h2
        className="text-base font-semibold mb-3"
        style={{ color: '#24292f' }}
      >
        {title}
      </h2>
      <div
        className="rounded border"
        style={{
          border: '1px solid #e1e4e8',
          backgroundColor: hasError ? '#fff8f0' : 'white',
        }}
      >
        {code ? (
          <div
            style={{
              backgroundColor: '#f6f8fa',
              padding: '16px',
              fontFamily: 'monospace',
              fontSize: '13px',
              whiteSpace: 'pre-wrap',
              lineHeight: '1.6',
              color: '#24292f',
            }}
          >
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        ) : (
          <div
            style={{ padding: '16px' }}
            className="prose prose-sm max-w-none"
          >
            <ReactMarkdown
              components={{
                h1: ({node, ...props}) => (
                  <h1 style={{fontSize:'18px', fontWeight:'700', color:'#24292f', marginBottom:'8px', marginTop:'16px'}} {...props} />
                ),
                h2: ({node, ...props}) => (
                  <h2 style={{fontSize:'15px', fontWeight:'600', color:'#24292f', marginBottom:'6px', marginTop:'16px', paddingBottom:'4px', borderBottom:'1px solid #e1e4e8'}} {...props} />
                ),
                h3: ({node, ...props}) => (
                  <h3 style={{fontSize:'13px', fontWeight:'600', color:'#24292f', marginBottom:'4px', marginTop:'12px'}} {...props} />
                ),
                p: ({node, ...props}) => (
                  <p style={{fontSize:'13px', lineHeight:'1.7', color:'#24292f', marginBottom:'10px'}} {...props} />
                ),
                li: ({node, ...props}) => (
                  <li style={{fontSize:'13px', lineHeight:'1.7', color:'#24292f', marginBottom:'4px'}} {...props} />
                ),
                ul: ({node, ...props}) => (
                  <ul style={{paddingLeft:'20px', marginBottom:'10px'}} {...props} />
                ),
                ol: ({node, ...props}) => (
                  <ol style={{paddingLeft:'20px', marginBottom:'10px'}} {...props} />
                ),
                strong: ({node, ...props}) => (
                  <strong style={{fontWeight:'600', color:'#24292f'}} {...props} />
                ),
                code: ({node, ...props}) => (
                  <code style={{backgroundColor:'#f6f8fa', padding:'2px 6px', borderRadius:'4px', fontFamily:'monospace', fontSize:'12px'}} {...props} />
                ),
                pre: ({node, ...props}) => (
                  <pre style={{backgroundColor:'#f6f8fa', border:'1px solid #e1e4e8', borderRadius:'6px', padding:'12px', fontFamily:'monospace', fontSize:'12px', overflowX:'auto', marginBottom:'10px'}} {...props} />
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
