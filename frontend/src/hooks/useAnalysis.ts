import { useState, useEffect, useRef } from 'react';
import { triggerAnalysis, getTaskStatus, waitForServer } from '../api/client';
import type { AnalysisRequest, TaskStatus } from '../types';

const STORAGE_KEY = 'repo_intel_active_task';

export function useAnalysis() {
  const [taskId, setTaskId] = useState<string | null>(() => {
    return sessionStorage.getItem(STORAGE_KEY);
  });
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [wakingUp, setWakingUp] = useState(false);
  const [wakeSeconds, setWakeSeconds] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const statusFailureCountRef = useRef(0);

  const startAnalysis = async (data: AnalysisRequest) => {
    setLoading(true);
    setError(null);
    setTaskStatus(null);
    statusFailureCountRef.current = 0;

    // 1) Make sure the server is awake BEFORE the POST (the POST is never auto-retried,
    //    so an analysis cannot be started twice and the daily rate limit is not wasted)
    setWakingUp(true);
    const awake = await waitForServer((s) => setWakeSeconds(s));
    setWakingUp(false);
    if (!awake) {
      setError('The server is still waking up. Please try again in a minute.');
      setLoading(false);
      return;
    }

    // 2) Now start the analysis (single attempt)
    try {
      const res = await triggerAnalysis(data);
      sessionStorage.setItem(STORAGE_KEY, res.task_id);
      setTaskId(res.task_id);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Could not start the analysis. Please try again.');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!taskId) return;

    setLoading(true);
    const poll = async () => {
      try {
        const status = await getTaskStatus(taskId);
        statusFailureCountRef.current = 0;
        setReconnecting(false);
        setTaskStatus(status);

        if (status.status === 'completed' || status.status === 'failed' || status.status === 'queued') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          sessionStorage.removeItem(STORAGE_KEY);
          setLoading(false);
          // If failed, set error message
          if (status.status === 'failed') {
            setError(status.error || 'Analysis failed. Please try again.');
          }
        }
      } catch (e) {
        statusFailureCountRef.current += 1;
        setReconnecting(true);
        if (statusFailureCountRef.current >= 48) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          sessionStorage.removeItem(STORAGE_KEY);
          setError('Unable to reach the backend after several minutes. Please try again shortly.');
          setLoading(false);
          setReconnecting(false);
        }
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId]);

  return { startAnalysis, taskStatus, loading, error, taskId, reconnecting, wakingUp, wakeSeconds };
}
