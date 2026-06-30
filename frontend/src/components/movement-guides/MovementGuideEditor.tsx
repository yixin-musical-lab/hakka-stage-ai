import { Button } from "../ui/button";
import { TextareaField, TextField } from "../ui/FormFields";
import type {
  MovementAssetStatus,
  MovementAssetType,
  MovementGuideContent,
  MovementMediaAsset,
  MovementStepDetail,
} from "../../types";

const assetTypeOptions: { value: MovementAssetType; label: string }[] = [
  { value: "reference_video", label: "老师参考视频" },
  { value: "skeleton_preview", label: "骨骼动画候选" },
  { value: "confirmed_skeleton", label: "标准骨骼示范" },
  { value: "digital_human_video", label: "真人/数字人视频" },
  { value: "courseware_video", label: "课件展示视频" },
  { value: "image", label: "图片材料" },
];

const assetStatusOptions: { value: MovementAssetStatus; label: string }[] = [
  { value: "draft", label: "草稿" },
  { value: "candidate", label: "候选" },
  { value: "confirmed", label: "已确认" },
  { value: "rejected", label: "不采用" },
];

export function MovementGuideEditor({
  content,
  modelInfo,
  onChange,
}: {
  content: MovementGuideContent;
  modelInfo: Record<string, unknown> | null;
  onChange: (content: MovementGuideContent) => void;
}) {
  function updateValue<Key extends keyof MovementGuideContent>(key: Key, value: MovementGuideContent[Key]) {
    onChange({ ...content, [key]: value });
  }

  return (
    <div className="lesson-editor">
      <section className="edit-section">
        <h3>基础信息</h3>
        <TextField label="材料标题" value={content.title} onChange={(value) => updateValue("title", value)} />
        <div className="field-grid">
          <TextField label="动作名称" value={content.action_name} onChange={(value) => updateValue("action_name", value)} />
          <TextField
            label="适用课程"
            value={content.course_context}
            required={false}
            onChange={(value) => updateValue("course_context", value)}
          />
        </div>
        <TextareaField
          label="动作描述"
          value={content.action_description}
          rows={5}
          onChange={(value) => updateValue("action_description", value)}
        />
        <div className="field-grid">
          <TextField label="动作节拍" value={content.beats} required={false} onChange={(value) => updateValue("beats", value)} />
          <TextField
            label="身体方向"
            value={content.body_direction}
            required={false}
            onChange={(value) => updateValue("body_direction", value)}
          />
          <TextField label="难度要求" value={content.difficulty} required={false} onChange={(value) => updateValue("difficulty", value)} />
        </div>
        <TextareaField
          label="规范动作脚本"
          value={content.normalized_motion_script}
          required={false}
          rows={4}
          onChange={(value) => updateValue("normalized_motion_script", value)}
        />
      </section>

      <StepList values={content.breakdown_steps} onChange={(values) => updateValue("breakdown_steps", values)} />
      <EditableTextList title="节奏提示" values={content.rhythm_tips} onChange={(values) => updateValue("rhythm_tips", values)} />
      <EditableTextList title="常见错误" values={content.common_mistakes} onChange={(values) => updateValue("common_mistakes", values)} />
      <EditableTextList title="纠正话术" values={content.correction_cues} onChange={(values) => updateValue("correction_cues", values)} />
      <EditableTextList title="教学提示" values={content.teaching_tips} onChange={(values) => updateValue("teaching_tips", values)} />
      <MediaAssetList values={content.media_assets} onChange={(values) => updateValue("media_assets", values)} />

      <TextareaField
        label="老师复核说明"
        value={content.teacher_review_notes}
        required={false}
        rows={4}
        onChange={(value) => updateValue("teacher_review_notes", value)}
      />
      {modelInfo ? <PipelineInfo modelInfo={modelInfo} /> : null}
    </div>
  );
}

function StepList({ values, onChange }: { values: MovementStepDetail[]; onChange: (values: MovementStepDetail[]) => void }) {
  return (
    <section className="edit-section">
      <div className="section-heading">
        <div>
          <p className="section-kicker">动作图解</p>
          <h3>动作步骤拆解</h3>
        </div>
        <Button variant="secondary" type="button" onClick={addStep}>
          添加步骤
        </Button>
      </div>
      {values.map((step, index) => (
        <div className="nested-editor" key={`movement-step-${index}`}>
          <div className="activity-row">
            <input value={step.name} onChange={(event) => updateStep(index, { ...step, name: event.target.value })} aria-label="步骤名称" />
            <input value={step.beats} onChange={(event) => updateStep(index, { ...step, beats: event.target.value })} aria-label="对应节拍" />
            <Button variant="destructive" type="button" onClick={() => removeStep(index)}>
              删除
            </Button>
          </div>
          <textarea
            value={step.description}
            rows={3}
            onChange={(event) => updateStep(index, { ...step, description: event.target.value })}
            aria-label="步骤说明"
          />
          <textarea
            value={step.teacher_cue}
            rows={2}
            onChange={(event) => updateStep(index, { ...step, teacher_cue: event.target.value })}
            aria-label="老师口令"
          />
        </div>
      ))}
    </section>
  );

  function addStep() {
    onChange([...values, { name: "新步骤", beats: "", description: "", teacher_cue: "" }]);
  }

  function updateStep(index: number, nextValue: MovementStepDetail) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }

  function removeStep(index: number) {
    onChange(values.filter((_, valueIndex) => valueIndex !== index));
  }
}

function EditableTextList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <section className="edit-section compact-section">
      <div className="section-heading">
        <div>
          <p className="section-kicker">教学说明</p>
          <h3>{title}</h3>
        </div>
        <Button variant="secondary" type="button" onClick={() => onChange([...values, ""])}>
          添加
        </Button>
      </div>
      {values.map((value, index) => (
        <div className="inline-edit-row" key={`${title}-${index}`}>
          <textarea
            value={value}
            rows={2}
            onChange={(event) => onChange(values.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))}
          />
          <Button variant="destructive" type="button" onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}>
            删除
          </Button>
        </div>
      ))}
    </section>
  );
}

function MediaAssetList({ values, onChange }: { values: MovementMediaAsset[]; onChange: (values: MovementMediaAsset[]) => void }) {
  return (
    <section className="edit-section">
      <div className="section-heading">
        <div>
          <p className="section-kicker">示范材料</p>
          <h3>视频 / 图片材料</h3>
        </div>
        <Button variant="secondary" type="button" onClick={addAsset}>
          添加材料
        </Button>
      </div>
      {values.map((asset, index) => (
        <div className="nested-editor" key={`movement-asset-${index}`}>
          <div className="field-grid">
            <input value={asset.title} onChange={(event) => updateAsset(index, { ...asset, title: event.target.value })} aria-label="材料标题" />
            <select
              value={asset.asset_type}
              onChange={(event) => updateAsset(index, { ...asset, asset_type: event.target.value as MovementAssetType })}
              aria-label="材料类型"
            >
              {assetTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={asset.status}
              onChange={(event) => updateAsset(index, { ...asset, status: event.target.value as MovementAssetStatus })}
              aria-label="材料状态"
            >
              {assetStatusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <input value={asset.url} onChange={(event) => updateAsset(index, { ...asset, url: event.target.value })} aria-label="材料链接" />
          <textarea
            value={asset.notes}
            rows={2}
            onChange={(event) => updateAsset(index, { ...asset, notes: event.target.value })}
            aria-label="材料备注"
          />
          <Button variant="destructive" type="button" onClick={() => removeAsset(index)}>
            删除材料
          </Button>
        </div>
      ))}
    </section>
  );

  function addAsset() {
    onChange([...values, { asset_type: "reference_video", title: "新示范材料", url: "", status: "draft", notes: "" }]);
  }

  function updateAsset(index: number, nextValue: MovementMediaAsset) {
    onChange(values.map((value, valueIndex) => (valueIndex === index ? nextValue : value)));
  }

  function removeAsset(index: number) {
    onChange(values.filter((_, valueIndex) => valueIndex !== index));
  }
}

function PipelineInfo({ modelInfo }: { modelInfo: Record<string, unknown> }) {
  return (
    <p className="model-info">
      生成链路：{String(modelInfo.pipeline ?? "manual_first_stage")} / Kimodo {String(modelInfo.kimodo ?? "not_connected")} / 数字人视频{" "}
      {String(modelInfo.digital_human_video ?? "not_connected")}
    </p>
  );
}
