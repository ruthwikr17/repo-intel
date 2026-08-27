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
  repo_id: number;
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
