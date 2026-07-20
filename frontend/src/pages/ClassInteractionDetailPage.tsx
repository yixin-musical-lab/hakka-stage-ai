import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ClassInteractionEditor } from "../components/class-interactions/ClassInteractionEditor";
import { StudioLayout } from "../components/studio/StudioLayout";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchClassInteraction, updateClassInteraction } from "../lib/api";
import { downloadClassInteractionMarkdown } from "../lib/download";
import type { ClassInteractionContent, ClassInteractionResponse } from "../types";

export function ClassInteractionDetailPage() {
  const { classInteractionId } = useParams();
  const navigate = useNavigate();
  const [interaction, setInteraction] = useState<ClassInteractionResponse | null>(null);
  const [editedContent, setEditedContent] = useState<ClassInteractionContent | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!classInteractionId) {
      return;
    }
    void fetchClassInteraction(classInteractionId)
      .then((detail) => { setInteraction(detail); setEditedContent(detail.edited_content ?? detail.content); setNotice(""); })
      .catch((caughtError) => setNotice(caughtError instanceof Error ? caughtError.message : "读取课堂互动方案失败。"))
      .finally(() => setLoading(false));
  }, [classInteractionId]);

  async function saveInteraction() {
    if (!interaction || !editedContent) {
      return;
    }
    setSaving(true);
    setNotice("");
    try {
      const updated = await updateClassInteraction(interaction.id, editedContent);
      setInteraction(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      setNotice("老师编辑稿已保存。");
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload() {
    if (!interaction) {
      return;
    }
    try {
      setNotice("");
      await downloadClassInteractionMarkdown(interaction.id, interaction.title);
    } catch (caughtError) {
      setNotice(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="课堂互动详情"
        title={interaction?.title ?? "读取课堂互动方案"}
        description="查看、继续修改并导出老师确认稿。"
        action={<div className="button-row"><Button variant="secondary" type="button" onClick={() => navigate("/interactions")}>返回列表</Button>{interaction ? <Button variant="secondary" type="button" onClick={() => void handleDownload()}>导出 Markdown</Button> : null}<Button type="button" disabled={!editedContent || saving} onClick={() => void saveInteraction()}>{saving ? "保存中..." : "保存全部修改"}</Button></div>}
      />
      <StudioLayout mode="edit" currentStep={interaction?.edited_content ? 3 : 2}>
        {notice ? <p className="notice">{notice}</p> : null}
        {loading ? <EmptyState title="正在读取课堂互动方案" text="请稍候，系统正在读取详情。" /> : null}
        {editedContent ? <Card asChild className="surface-panel"><section><ClassInteractionEditor content={editedContent} onChange={setEditedContent} modelInfo={interaction?.raw_model_info ?? null} /></section></Card> : !loading ? <EmptyState title="课堂互动内容不可用" text="这份方案可能尚未生成成功，暂时无法编辑或导出。" /> : null}
      </StudioLayout>
    </main>
  );
}
