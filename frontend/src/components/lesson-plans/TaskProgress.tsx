import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";
import type { AiTaskResponse } from "../../types";

export function TaskProgress({ task }: { task: AiTaskResponse | null }) {
  const actualProgress = task?.progress ?? 0;
  const [displayProgress, setDisplayProgress] = useState(actualProgress);
  const taskStatus = task?.status ?? "IDLE";
  const taskId = task?.id ?? "";

  useEffect(() => {
    setDisplayProgress(actualProgress);
  }, [actualProgress, taskId]);

  useEffect(() => {
    if (!task) {
      setDisplayProgress(0);
      return;
    }

    if (task.status === "FAILED" || task.status === "CANCELLED") {
      setDisplayProgress(actualProgress);
      return;
    }

    const timer = window.setInterval(() => {
      setDisplayProgress((current) => {
        const targetProgress =
          taskStatus === "SUCCESS"
            ? 100
            : taskStatus === "PENDING"
              ? Math.max(actualProgress, 6)
              : taskStatus === "RUNNING"
                ? Math.min(Math.max(actualProgress, current + 0.8), 92)
                : actualProgress;

        if (task.status === "SUCCESS") {
          return Math.min(current + 8, 100);
        }
        if (current >= targetProgress) {
          return current;
        }
        const distance = targetProgress - current;
        return Math.min(current + Math.max(distance * 0.32, 0.6), targetProgress);
      });
    }, 220);

    return () => window.clearInterval(timer);
  }, [actualProgress, task, taskStatus]);

  const visibleProgress = Math.round(displayProgress);
  const progressState = visibleProgress >= 100 || task?.status === "SUCCESS" ? "complete" : "active";

  return (
    <div className="task-line">
      <div>
        <span>任务状态</span>
        <strong>{task ? `${task.status} · ${visibleProgress}%` : "未提交"}</strong>
      </div>
      <Progress aria-hidden="true" className="task-progress-bar" data-state={progressState} value={displayProgress} />
    </div>
  );
}
