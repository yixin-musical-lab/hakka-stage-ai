from app.models.class_interaction import ClassInteraction
from app.models.lesson_plan import AiTask, Course, LessonPlan, LessonPlanVariant
from app.models.media_generation import (
    MediaAsset,
    MediaGeneration,
    MediaWorkbenchConfig,
    ProviderTaskRun,
    WorkflowTemplate,
    WorkflowTemplateVersion,
)
from app.models.movement_guide import MovementGuide
from app.models.musical import MusicalFusionPlan, MusicalProject, MusicalScript, RoleTrainingPlan, SongAdaptation
from app.models.practice import PracticeReport, PracticeSubmission
from app.models.rehearsal_review import RehearsalReview
from app.models.user import User

__all__ = [
    "AiTask",
    "ClassInteraction",
    "Course",
    "LessonPlan",
    "LessonPlanVariant",
    "MovementGuide",
    "MediaAsset",
    "MediaGeneration",
    "MediaWorkbenchConfig",
    "MusicalFusionPlan",
    "MusicalProject",
    "PracticeReport",
    "PracticeSubmission",
    "ProviderTaskRun",
    "RehearsalReview",
    "MusicalScript",
    "RoleTrainingPlan",
    "SongAdaptation",
    "User",
    "WorkflowTemplate",
    "WorkflowTemplateVersion",
]
