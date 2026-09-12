import axios from 'axios';
import type {
  AnalysisRequest, TaskStatus, Analysis,
  Repository, Opportunity, UserProfile
} from '../types';

const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api`
  : '/api';

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  // A stuck connection should become a retryable polling error, rather than
  // leaving the progress view spinning forever.
  timeout: 15_000,
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

export const getAnalytics = async () => {
  const res = await api.get('/analytics/overview');
  return res.data;
};
