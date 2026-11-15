import axios from 'axios';
import type {
  AnalysisRequest, TaskStatus, Analysis,
  Repository, Opportunity, UserProfile
} from '../types';

export const API_BASE: string = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60_000,
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config: any = error.config;
    if (!config || config.__noRetry) return Promise.reject(error);

    const isGet = (config.method || '').toLowerCase() === 'get';
    const isStatusPoll = (config.url || '').includes('/analyze/status');
    const status = error.response?.status;
    // No response (timeout / network / CORS-less cold start) or gateway errors
    const retryable = !error.response || [502, 503, 504].includes(status);

    if (!isGet || isStatusPoll || !retryable) return Promise.reject(error);

    config.__retryCount = (config.__retryCount || 0) + 1;
    if (config.__retryCount > 4) return Promise.reject(error);

    await new Promise((r) => setTimeout(r, 2000 * config.__retryCount));
    return api(config);
  }
);

export const pingServer = async (timeoutMs = 8000): Promise<boolean> => {
  try {
    await api.get('/ping', { timeout: timeoutMs, __noRetry: true } as any);
    return true;
  } catch {
    return false;
  }
};

export const waitForServer = async (
  onWaiting?: (secondsWaited: number) => void,
  maxWaitMs = 120000
): Promise<boolean> => {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    if (await pingServer()) return true;
    onWaiting?.(Math.round((Date.now() - start) / 1000));
    await new Promise((r) => setTimeout(r, 3000));
  }
  return false;
};

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
