import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { MusicalFusionEditor } from "../components/musical/MusicalFusionEditor";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchMusicalFusionPlan, updateMusicalFusionPlan } from "../lib/api";
import { downloadMusicalFusionMarkdown } from "../lib/download";
import type { MusicalFusionContent, MusicalFusionPlanResponse } from "../types";

export function MusicalFusionPlanDetailPage() {
  const { musicalFusionPlanId } = useParams();
  const navigate = useNavigate();
  const [plan, setPlan] = useState<MusicalFusionPlanResponse | null>(null);
  const [editedContent, setEditedContent] = useState<MusicalFusionContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!musicalFusionPlanId) {
      return;
    }
    void fetchMusicalFusionPlan(musicalFusionPlanId)
      .then((detail) => {
        setPlan(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setNotice("");
      })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取歌舞融合方案失败。"))
      .finally(() => setLoading(false));
  }, [musicalFusionPlanId]);

  async function savePlan() {
    if (!plan || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateMusicalFusionPlan(plan.id, editedContent);
      setPlan(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("编导编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownloadMarkdown() {
    if (!plan) {
      return;
    }
    try {
      setNotice("");
      await downloadMusicalFusionMarkdown(plan.id, plan.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  async function openRoleTraining() {
    if (!plan || !editedContent) {
      return;
    }
    try {
      // 进入下游 M05 前先保存当前编辑稿，确保训练任务读取到编导刚确认的内容。
      await updateMusicalFusionPlan(plan.id, editedContent);
      navigate(`/role-training-plans/generate?script_id=${plan.script_id}&fusion_plan_id=${plan.id}`);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存并打开训练计划失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="M04 歌舞融合详情"
        title={plan?.title ?? "读取歌舞融合方案"}
        description="查看、修改并导出编导确认稿，也可以把本方案带入分角色训练计划。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/musical-fusion-plans")}>
              返回列表
            </Button>
            {plan?.song_adaptation_id ? (
              <Button variant="secondary" type="button" onClick={() => navigate(`/song-adaptations/${plan.song_adaptation_id}`)}>
                查看来源唱段
              </Button>
            ) : null}
            {plan ? (
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving} onClick={() => void savePlan()}>
              {saving ? "保存中..." : "保存全部修改"}
            </Button>
          </div>
        }
      />

      {plan ? (
        <div className="readable-chip-row">
          <Badge variant="secondary">{plan.source_mode === "song_adaptation" ? "引用 M03" : "手工音乐段落"}</Badge>
          <Badge variant="outline">{plan.music_title || "未标注音乐"}</Badge>
        </div>
      ) : null}
      {notice ? <p className="notice">{notice}</p> : null}
      {loading ? <EmptyState title="正在读取歌舞融合方案" text="请稍候，系统正在加载编导结构。" /> : null}

      {editedContent ? (
        <>
          <Card asChild className="surface-panel">
            <section>
              <MusicalFusionEditor content={editedContent} onChange={setEditedContent} modelInfo={plan?.raw_model_info ?? null} />
            </section>
          </Card>
          <Card asChild className="surface-panel next-step-panel">
            <section>
              <div className="section-heading">
                <div>
                  <p className="section-kicker">下一步 · M05</p>
                  <h2>把歌舞融合结构带入分角色训练</h2>
                  <p>训练计划会读取本方案的演唱角色、舞蹈形式、队形、高潮和排练提示。</p>
                </div>
                <Button type="button" onClick={() => void openRoleTraining()}>
                  基于本方案生成训练计划
                </Button>
              </div>
            </section>
          </Card>
        </>
      ) : !loading ? (
        <EmptyState title="歌舞融合内容不可用" text="这份方案可能尚未生成成功，暂时无法编辑或导出。" />
      ) : null}
    </main>
  );
}
