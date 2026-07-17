import type { LessonPlanVariantForm, LessonPlanVariantType } from "../types";

export const lessonPlanVariantOptions: Array<{
  id: LessonPlanVariantType;
  label: string;
  description: string;
}> = [
  { id: "younger", label: "低龄版", description: "短口令、低难度、强趣味与安全重复" },
  { id: "basic", label: "基础版", description: "慢推进、细分解、强化节拍与纠正" },
  { id: "advanced", label: "进阶版", description: "提升连接、协作、方向和表现要求" },
  { id: "performance", label: "演出版", description: "强化队形、衔接、舞台表达与连排" },
];

export function lessonPlanVariantLabel(variantType: LessonPlanVariantType | null | undefined) {
  return lessonPlanVariantOptions.find((option) => option.id === variantType)?.label ?? "原教案";
}

export function initialLessonPlanVariantForm(
  provider: LessonPlanVariantForm["llm_provider"] = "deepseek",
  model = "deepseek-v4-flash",
  reasoningLevel: LessonPlanVariantForm["reasoning_level"] = "standard",
): LessonPlanVariantForm {
  return {
    variant_type: "younger",
    adjustment_direction: "",
    llm_provider: provider,
    llm_model: model,
    reasoning_level: reasoningLevel,
  };
}
