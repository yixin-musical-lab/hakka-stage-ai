import { ArrowRight, Check, Circle, Library, ShieldCheck, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { useLayoutPreference } from "../../contexts/LayoutPreferenceContext";

type StudioLayoutProps = {
  children: ReactNode;
  currentStep?: 1 | 2 | 3;
  mode?: "compose" | "edit";
  libraryTo?: string;
  libraryLabel?: string;
  status?: ReactNode;
  note?: string;
};

const composeSteps = [
  { title: "设置生成条件", description: "补充来源、目标与约束" },
  { title: "AI 生成初稿", description: "查看任务状态与结构化结果" },
  { title: "人工编辑确认", description: "修改、保存并进入后续阶段" },
];

const editSteps = [
  { title: "检查 AI 初稿", description: "核对结构与事实是否完整" },
  { title: "人工编辑内容", description: "逐段调整课堂或排演细节" },
  { title: "保存确认稿", description: "保存后再导出或进入下一阶段" },
];

/**
 * 方案 D 的公共工作室外壳。
 * 组件只负责布局和真实流程提示，不复制业务状态、表单或编辑器，避免响应式切换时造成输入内容丢失。
 */
export function StudioLayout({
  children,
  currentStep = 1,
  mode = "compose",
  libraryTo,
  libraryLabel = "查看已保存内容",
  status,
  note = "AI 生成内容仅作为初稿，保存或进入下一阶段前请由老师完成检查。",
}: StudioLayoutProps) {
  const { layoutMode } = useLayoutPreference();
  const steps = mode === "edit" ? editSteps : composeSteps;
  const classicMode = layoutMode === "classic";

  return (
    <div className={`studio-layout${classicMode ? " studio-layout--classic" : ""}`} data-mode={mode}>
      <div className="studio-workspace">{children}</div>

      {!classicMode ? <aside className="studio-inspector" aria-label="工作室流程">
        <div className="studio-inspector-heading">
          <span><Sparkles aria-hidden /></span>
          <div><p className="section-kicker">AI 工作室</p><h2>工作流程</h2></div>
        </div>

        {status ? <div className="studio-current-status" aria-live="polite">{status}</div> : null}

        <ol className="studio-steps">
          {steps.map((step, index) => {
            const stepNumber = index + 1;
            const complete = stepNumber < currentStep;
            const current = stepNumber === currentStep;
            return (
              <li className={`${complete ? "is-complete" : ""}${current ? " is-current" : ""}`} key={step.title}>
                <span>{complete ? <Check aria-hidden /> : <Circle aria-hidden />}</span>
                <div><strong>{step.title}</strong><small>{step.description}</small></div>
              </li>
            );
          })}
        </ol>

        <div className="studio-review-note">
          <ShieldCheck aria-hidden />
          <p>{note}</p>
        </div>

        {libraryTo ? (
          <Link className="studio-library-link" to={libraryTo}>
            <Library aria-hidden />
            <span>{libraryLabel}</span>
            <ArrowRight aria-hidden />
          </Link>
        ) : null}
      </aside> : null}
    </div>
  );
}
