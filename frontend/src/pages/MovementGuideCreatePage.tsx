import { useState } from "react";
import { useNavigate } from "react-router";
import { TextareaField, TextField } from "../components/ui/FormFields";
import { PageTitle } from "../components/ui/PageTitle";
import { createMovementGuide } from "../lib/api";
import { initialMovementGuideForm } from "../lib/lessonPlanDefaults";
import type { MovementGuideForm } from "../types";

export function MovementGuideCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<MovementGuideForm>(initialMovementGuideForm);
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submitMovementGuide(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setSubmitting(true);
    setNotice("");
    try {
      const created = await createMovementGuide(form);
      navigate(`/movement-guides/${created.id}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "创建动作图解失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="示范材料"
        title="新建动作图解"
        description="先录入动作描述、节拍、方向和教学提示，生成一份可编辑的动作拆解材料。"
        action={
          <button className="secondary-button" type="button" onClick={() => navigate("/movement-guides")}>
            已保存材料
          </button>
        }
      />

      <section className="lesson-layout">
        <form className="surface-panel input-panel" onSubmit={submitMovementGuide}>
          <div className="section-heading">
            <div>
              <p className="section-kicker">T03</p>
              <h2>动作说明</h2>
            </div>
            <button className="secondary-button" type="button" onClick={fillExample}>
              填入示例
            </button>
          </div>

          <div className="field-grid">
            <TextField label="动作名称" value={form.action_name} onChange={(value) => updateForm("action_name", value)} />
            <TextField
              label="适用课程"
              value={form.course_context}
              required={false}
              onChange={(value) => updateForm("course_context", value)}
            />
          </div>
          <TextareaField label="动作描述" value={form.action_description} rows={5} onChange={(value) => updateForm("action_description", value)} />
          <div className="field-grid">
            <TextField label="动作节拍" value={form.beats} required={false} onChange={(value) => updateForm("beats", value)} />
            <TextField label="身体方向" value={form.body_direction} required={false} onChange={(value) => updateForm("body_direction", value)} />
            <TextField label="难度要求" value={form.difficulty} required={false} onChange={(value) => updateForm("difficulty", value)} />
          </div>
          <TextareaField label="教学提示" value={form.teaching_tips} required={false} onChange={(value) => updateForm("teaching_tips", value)} />
          <TextField
            label="老师参考视频链接"
            value={form.reference_video_url}
            required={false}
            onChange={(value) => updateForm("reference_video_url", value)}
          />
          <TextField
            label="数字人形象图链接"
            value={form.digital_human_image_url}
            required={false}
            onChange={(value) => updateForm("digital_human_image_url", value)}
          />

          {notice ? <p className="notice">{notice}</p> : null}
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "创建中..." : "创建动作图解"}
          </button>
        </form>

        <aside className="surface-panel result-panel">
          <div className="section-heading">
            <div>
              <p className="section-kicker">当前范围</p>
              <h2>第一阶段先做材料管理</h2>
            </div>
          </div>
          <div className="empty-state">
            <h3>不在本机直接生成重视频</h3>
            <p>
              当前会保存动作拆解、关键提示和材料链接；Kimodo 骨骼动画、真人 / 数字人视频生成后续接入 Worker 和云端 GPU。
            </p>
          </div>
        </aside>
      </section>
    </main>
  );

  function updateForm<Key extends keyof MovementGuideForm>(key: Key, value: MovementGuideForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function fillExample() {
    setForm(initialMovementGuideForm);
  }
}
