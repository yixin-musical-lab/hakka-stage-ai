import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { MusicalCreationFlowPanel, type MusicalCreationStage } from "../components/musical/MusicalCreationFlowPanel";
import { MusicalScriptEditor } from "../components/musical/MusicalScriptEditor";
import { StudioLayout } from "../components/studio/StudioLayout";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { EmptyState } from "../components/ui/EmptyState";
import { PageTitle } from "../components/ui/PageTitle";
import { fetchMusicalScript, updateMusicalScript } from "../lib/api";
import { downloadMusicalScriptMarkdown } from "../lib/download";
import type { MusicalScriptContent, MusicalScriptResponse } from "../types";

type MessageType = "status" | "error";

export function MusicalScriptDetailPage() {
  const { musicalScriptId } = useParams();
  const navigate = useNavigate();
  const [musicalScript, setMusicalScript] = useState<MusicalScriptResponse | null>(null);
  const [editedContent, setEditedContent] = useState<MusicalScriptContent | null>(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<MessageType>("status");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [openingStage, setOpeningStage] = useState<MusicalCreationStage | null>(null);

  useEffect(() => {
    if (!musicalScriptId) {
      setLoading(false);
      return;
    }
    void fetchMusicalScript(musicalScriptId)
      .then((detail) => {
        setMusicalScript(detail);
        setEditedContent(detail.edited_content ?? detail.content);
        setMessage("");
      })
      .catch((caughtError) => showError(caughtError instanceof Error ? caughtError.message : "读取剧本失败。"))
      .finally(() => setLoading(false));
  }, [musicalScriptId]);

  async function saveMusicalScript() {
    if (!musicalScript || !editedContent || saving) {
      return;
    }
    setSaving(true);
    showStatus("正在保存剧本确认稿……");
    try {
      const updated = await updateMusicalScript(musicalScript.id, editedContent);
      setMusicalScript(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      showStatus("编导编辑稿已保存。");
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "保存剧本失败。");
    } finally {
      setSaving(false);
    }
  }

  async function openCreationStage(stage: MusicalCreationStage, path: string) {
    if (!musicalScript || !editedContent || saving || openingStage) {
      return;
    }
    setOpeningStage(stage);
    showStatus("正在保存剧本确认稿并打开下一步……");
    try {
      // 下游任务读取剧本编辑确认稿，因此跳转前统一保存，避免新任务带入旧版本。
      const updated = await updateMusicalScript(musicalScript.id, editedContent);
      setMusicalScript(updated);
      setEditedContent(updated.edited_content ?? updated.content);
      navigate(path);
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "保存剧本并打开创编任务失败。");
      setOpeningStage(null);
    }
  }

  async function handleDownloadMarkdown() {
    if (!musicalScript) {
      return;
    }
    try {
      await downloadMusicalScriptMarkdown(musicalScript.id, musicalScript.title);
      showStatus("剧本 Markdown 已开始下载。");
    } catch (caughtError) {
      showError(caughtError instanceof Error ? caughtError.message : "导出 Markdown 失败。");
    }
  }

  return (
    <main className="page-frame">
      <PageTitle
        eyebrow="剧本详情"
        title={musicalScript?.title ?? "读取剧本"}
        description="查看、继续修改并导出编导确认稿；确认后可沿创编流程继续完成唱段、歌舞融合和分角色训练。"
        action={
          <div className="button-row">
            <Button variant="secondary" type="button" onClick={() => navigate("/musical-scripts")}>
              返回列表
            </Button>
            {musicalScript ? (
              <Button variant="secondary" type="button" onClick={() => void handleDownloadMarkdown()}>
                导出 Markdown
              </Button>
            ) : null}
            <Button type="button" disabled={!editedContent || saving || openingStage !== null} onClick={() => void saveMusicalScript()}>
              {saving ? "保存中……" : "保存全部修改"}
            </Button>
          </div>
        }
      />

      <StudioLayout mode="edit" currentStep={musicalScript?.edited_content ? 3 : 2}>
        {message ? (
          <p className="notice" role={messageType === "error" ? "alert" : "status"} aria-live={messageType === "error" ? "assertive" : "polite"}>
            {message}
          </p>
        ) : null}
        {loading ? <EmptyState title="正在读取剧本" text="请稍候，系统正在读取剧本详情。" /> : null}

        {musicalScript && editedContent ? (
          <MusicalCreationFlowPanel
            scriptId={musicalScript.id}
            disabled={saving}
            openingStage={openingStage}
            onCreate={openCreationStage}
            onOpen={navigate}
          />
        ) : null}

        <section className="script-detail-layout">
          <Card asChild className="surface-panel">
            <section>
              {editedContent ? (
                <MusicalScriptEditor content={editedContent} onChange={setEditedContent} modelInfo={musicalScript?.raw_model_info ?? null} />
              ) : !loading ? (
                <EmptyState title="剧本内容不可用" text="这份剧本可能尚未生成成功，暂时无法编辑、导出或进入下游创编任务。" />
              ) : null}
            </section>
          </Card>
        </section>
      </StudioLayout>
    </main>
  );

  function showStatus(nextMessage: string) {
    setMessageType("status");
    setMessage(nextMessage);
  }

  function showError(nextMessage: string) {
    setMessageType("error");
    setMessage(nextMessage);
  }
}
