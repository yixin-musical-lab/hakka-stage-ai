import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Shell } from "./components/layout/Shell";
import { ClassInteractionDetailPage } from "./pages/ClassInteractionDetailPage";
import { ClassInteractionGeneratePage } from "./pages/ClassInteractionGeneratePage";
import { ClassInteractionListPage } from "./pages/ClassInteractionListPage";
import { HealthPage } from "./pages/HealthPage";
import { HomePage } from "./pages/HomePage";
import { LessonPlanDetailPage } from "./pages/LessonPlanDetailPage";
import { LessonPlanGeneratePage } from "./pages/LessonPlanGeneratePage";
import { LessonPlanListPage } from "./pages/LessonPlanListPage";
import { MovementGuideCreatePage } from "./pages/MovementGuideCreatePage";
import { MovementGuideDetailPage } from "./pages/MovementGuideDetailPage";
import { MovementGuideListPage } from "./pages/MovementGuideListPage";
import { MusicalScriptDetailPage } from "./pages/MusicalScriptDetailPage";
import { MusicalScriptGeneratePage } from "./pages/MusicalScriptGeneratePage";
import { MusicalScriptListPage } from "./pages/MusicalScriptListPage";
import { PracticeSubmissionCreatePage } from "./pages/PracticeSubmissionCreatePage";
import { PracticeSubmissionDetailPage } from "./pages/PracticeSubmissionDetailPage";
import { PracticeSubmissionListPage } from "./pages/PracticeSubmissionListPage";
import { RoleTrainingPlanDetailPage } from "./pages/RoleTrainingPlanDetailPage";
import { RoleTrainingPlanListPage } from "./pages/RoleTrainingPlanListPage";
import { SongAdaptationDetailPage } from "./pages/SongAdaptationDetailPage";
import { SongAdaptationListPage } from "./pages/SongAdaptationListPage";

export function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lesson-plans/generate" element={<LessonPlanGeneratePage />} />
          <Route path="/lesson-plans" element={<LessonPlanListPage />} />
          <Route path="/lesson-plans/:lessonPlanId" element={<LessonPlanDetailPage />} />
          <Route path="/interactions/generate" element={<ClassInteractionGeneratePage />} />
          <Route path="/interactions" element={<ClassInteractionListPage />} />
          <Route path="/interactions/:classInteractionId" element={<ClassInteractionDetailPage />} />
          <Route path="/musical-scripts/generate" element={<MusicalScriptGeneratePage />} />
          <Route path="/musical-scripts" element={<MusicalScriptListPage />} />
          <Route path="/musical-scripts/:musicalScriptId" element={<MusicalScriptDetailPage />} />
          <Route path="/song-adaptations" element={<SongAdaptationListPage />} />
          <Route path="/song-adaptations/:songAdaptationId" element={<SongAdaptationDetailPage />} />
          <Route path="/role-training-plans" element={<RoleTrainingPlanListPage />} />
          <Route path="/role-training-plans/:roleTrainingPlanId" element={<RoleTrainingPlanDetailPage />} />
          <Route path="/movement-guides/new" element={<MovementGuideCreatePage />} />
          <Route path="/movement-guides" element={<MovementGuideListPage />} />
          <Route path="/movement-guides/:movementGuideId" element={<MovementGuideDetailPage />} />
          <Route path="/practice-submissions/new" element={<PracticeSubmissionCreatePage />} />
          <Route path="/practice-submissions" element={<PracticeSubmissionListPage />} />
          <Route path="/practice-submissions/:submissionId" element={<PracticeSubmissionDetailPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
