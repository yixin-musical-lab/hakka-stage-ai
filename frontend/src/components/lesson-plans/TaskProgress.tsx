import type { AiTaskResponse } from "../../types";

export function TaskProgress({ task }: { task: AiTaskResponse | null }) {
  const progress = task?.progress ?? 0;
  return (
    <div className="task-line">
      <div>
        <span>任务状态</span>
        <strong>{task ? `${task.status} · ${progress}%` : "未提交"}</strong>
      </div>
      <div className="progress-track" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
