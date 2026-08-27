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

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'queued') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setLoading(false);
          // If failed, set error message
          if (status.status === 'failed') {
            setError(status.error || 'Analysis failed. Please try again.');
          }
        }
      } catch (e) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setError('Failed to get analysis status. Check if backend is running.');
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
