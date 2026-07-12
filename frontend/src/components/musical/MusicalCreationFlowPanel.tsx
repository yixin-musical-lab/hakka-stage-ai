import { useEffect, useMemo, useState } from "react";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../ui/card";
import { Separator } from "../ui/separator";
import { fetchMusicalFusionPlans, fetchRehearsalReviews, fetchRoleTrainingPlans, fetchSongAdaptations } from "../../lib/api";
import type { MusicalFusionPlanSummary, RehearsalReviewSummary, RoleTrainingPlanSummary, SongAdaptationSummary } from "../../types";

export type MusicalCreationStage = "m03" | "m04" | "m05" | "m08";

type StageStatus = {
  label: string;
  tone: "default" | "secondary" | "destructive" | "outline";
};

export function MusicalCreationFlowPanel({
  scriptId,
  disabled,
  openingStage,
  onCreate,
  onOpen,
}: {
  scriptId: string;
  disabled: boolean;
  openingStage: MusicalCreationStage | null;
  onCreate: (stage: MusicalCreationStage, path: string) => Promise<void>;
  onOpen: (path: string) => void;
}) {
  const [songAdaptations, setSongAdaptations] = useState<SongAdaptationSummary[]>([]);
  const [fusionPlans, setFusionPlans] = useState<MusicalFusionPlanSummary[]>([]);
  const [trainingPlans, setTrainingPlans] = useState<RoleTrainingPlanSummary[]>([]);
  const [rehearsalReviews, setRehearsalReviews] = useState<RehearsalReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<Record<MusicalCreationStage, boolean>>({ m03: false, m04: false, m05: false, m08: false });

  useEffect(() => {
    const controller = new AbortController();

    async function loadStages() {
      const [songResult, fusionResult, trainingResult, reviewResult] = await Promise.allSettled([
        fetchSongAdaptations(controller.signal),
        fetchMusicalFusionPlans(controller.signal),
        fetchRoleTrainingPlans(controller.signal),
        fetchRehearsalReviews(controller.signal),
      ]);
      if (controller.signal.aborted) {
        return;
      }

      if (songResult.status === "fulfilled") {
        setSongAdaptations(songResult.value.filter((item) => item.script_id === scriptId));
      }
      if (fusionResult.status === "fulfilled") {
        setFusionPlans(fusionResult.value.filter((item) => item.script_id === scriptId));
      }
      if (trainingResult.status === "fulfilled") {
        setTrainingPlans(trainingResult.value.filter((item) => item.script_id === scriptId));
      }
      if (reviewResult.status === "fulfilled") {
        setRehearsalReviews(reviewResult.value.filter((item) => item.script_id === scriptId));
      }
      setErrors({
        m03: songResult.status === "rejected",
        m04: fusionResult.status === "rejected",
        m05: trainingResult.status === "rejected",
        m08: reviewResult.status === "rejected",
      });
      setLoading(false);
    }

    void loadStages();
    return () => controller.abort();
  }, [scriptId]);

  const stages = useMemo(() => {
    const latestSongAdaptation = songAdaptations[0] ?? null;
    const latestFusionPlan = fusionPlans[0] ?? null;
    const latestTrainingPlan = trainingPlans[0] ?? null;
    const latestRehearsalReview = rehearsalReviews[0] ?? null;
    const m04Query = latestSongAdaptation ? `&song_adaptation_id=${latestSongAdaptation.id}` : "";
    const m05Query = latestFusionPlan ? `&fusion_plan_id=${latestFusionPlan.id}` : "";
    const m08FusionQuery = latestFusionPlan ? `&fusion_plan_id=${latestFusionPlan.id}` : "";
    const m08TrainingQuery = latestTrainingPlan ? `&role_training_plan_id=${latestTrainingPlan.id}` : "";

    return [
      {
        key: "m03" as const,
        step: "01",
        eyebrow: "M03 唱段适配",
        title: "确定唱什么、谁来唱",
        description: "整理歌曲来源、歌词改写、演唱角色和舞蹈留白。",
        rows: songAdaptations,
        latestPath: latestSongAdaptation ? `/song-adaptations/${latestSongAdaptation.id}` : null,
        createPath: `/song-adaptations/generate?script_id=${scriptId}`,
      },
      {
        key: "m04" as const,
        step: "02",
        eyebrow: "M04 歌舞融合",
        title: "串联唱、跳、走位和队形",
        description: "把剧情和唱段整理成编导可排练的舞台段落结构。",
        rows: fusionPlans,
        latestPath: latestFusionPlan ? `/musical-fusion-plans/${latestFusionPlan.id}` : null,
        createPath: `/musical-fusion-plans/generate?script_id=${scriptId}${m04Query}`,
      },
      {
        key: "m05" as const,
        step: "03",
        eyebrow: "M05 分角色训练",
        title: "拆成按角色执行的训练任务",
        description: "按排练周期安排台词、演唱、舞蹈、走位和检查点。",
        rows: trainingPlans,
        latestPath: latestTrainingPlan ? `/role-training-plans/${latestTrainingPlan.id}` : null,
        createPath: `/role-training-plans/generate?script_id=${scriptId}${m05Query}`,
      },
      {
        key: "m08" as const,
        step: "04",
        eyebrow: "M08 排练 / 演出复盘",
        title: "把现场观察变成下一次行动",
        description: "整理问题、原因、角色任务、教学反思和下一次排练计划。",
        rows: rehearsalReviews,
        latestPath: latestRehearsalReview ? `/rehearsal-reviews/${latestRehearsalReview.id}` : null,
        createPath: `/rehearsal-reviews/generate?script_id=${scriptId}${m08FusionQuery}${m08TrainingQuery}`,
      },
    ];
  }, [fusionPlans, rehearsalReviews, scriptId, songAdaptations, trainingPlans]);

  return (
    <section className="creation-flow-section" aria-labelledby="creation-flow-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">创编流程</p>
          <h2 id="creation-flow-title">从剧本确认稿继续完成 M03 → M04 → M05 → M08</h2>
          <p>进入新任务前会自动保存当前剧本；查看已有结果不会修改剧本内容。</p>
        </div>
      </div>

      <div className="creation-flow-grid">
        {stages.map((stage) => {
          const stageStatus = getStageStatus(stage.rows[0]?.status, stage.rows.length, loading, errors[stage.key]);
          const isOpening = openingStage === stage.key;
          return (
            <Card className="creation-stage-card" key={stage.key}>
              <CardHeader>
                <div className="creation-stage-meta">
                  <span className="creation-stage-index" aria-hidden="true">{stage.step}</span>
                  <Badge variant={stageStatus.tone}>{stageStatus.label}</Badge>
                </div>
                <CardDescription>{stage.eyebrow}</CardDescription>
                <CardTitle>{stage.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{stage.description}</p>
                <Separator />
                <p className="creation-stage-count">
                  {errors[stage.key] ? "暂时无法读取已有记录" : loading ? "正在读取已有记录" : `当前已有 ${stage.rows.length} 份结果`}
                </p>
              </CardContent>
              <CardFooter className="creation-stage-actions">
                {stage.latestPath ? (
                  <Button variant="secondary" type="button" disabled={disabled || openingStage !== null} onClick={() => onOpen(stage.latestPath!)}>
                    查看最新结果
                  </Button>
                ) : null}
                <Button type="button" disabled={disabled || openingStage !== null} onClick={() => void onCreate(stage.key, stage.createPath)}>
                  {isOpening ? "正在保存并打开……" : stage.latestPath ? "新建一份" : "开始生成"}
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

function getStageStatus(status: string | undefined, count: number, loading: boolean, failed: boolean): StageStatus {
  if (loading) {
    return { label: "读取中", tone: "outline" };
  }
  if (failed) {
    return { label: "状态不可用", tone: "destructive" };
  }
  if (count === 0) {
    return { label: "未生成", tone: "outline" };
  }
  const normalized = status?.toLowerCase() ?? "";
  if (normalized.includes("fail")) {
    return { label: "最近失败", tone: "destructive" };
  }
  if (normalized.includes("generat") && normalized !== "generated") {
    return { label: "生成中", tone: "secondary" };
  }
  return { label: "已生成", tone: "default" };
}
