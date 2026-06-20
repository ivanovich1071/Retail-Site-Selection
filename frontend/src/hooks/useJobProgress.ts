import { useEffect, useRef, useState } from "react";
import { getAnalysisJob, type AnalysisJob } from "../services/api";

const TERMINAL = ["completed", "failed"];

/**
 * Polls an analysis job until it reaches a terminal state.
 * Polling (vs SSE) keeps it robust across proxies and the local stub server.
 */
export function useJobProgress(jobId: number | null, intervalMs = 1500) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setJob(null);
    setError(null);
    if (jobId == null) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const data = await getAnalysisJob(jobId);
        if (cancelled) return;
        setJob(data);
        if (TERMINAL.includes(data.status) && timer.current) {
          clearInterval(timer.current);
          timer.current = null;
        }
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.response?.data?.detail || "Не удалось получить статус задачи");
        if (timer.current) clearInterval(timer.current);
      }
    };

    poll();
    timer.current = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      if (timer.current) clearInterval(timer.current);
    };
  }, [jobId, intervalMs]);

  return { job, error, isDone: job ? TERMINAL.includes(job.status) : false };
}
