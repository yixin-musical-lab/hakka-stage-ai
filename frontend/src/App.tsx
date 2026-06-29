import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Shell } from "./components/layout/Shell";
import { HealthPage } from "./pages/HealthPage";
import { HomePage } from "./pages/HomePage";
import { LessonPlanDetailPage } from "./pages/LessonPlanDetailPage";
import { LessonPlanGeneratePage } from "./pages/LessonPlanGeneratePage";
import { LessonPlanListPage } from "./pages/LessonPlanListPage";
import { MusicalScriptDetailPage } from "./pages/MusicalScriptDetailPage";
import { MusicalScriptGeneratePage } from "./pages/MusicalScriptGeneratePage";
import { MusicalScriptListPage } from "./pages/MusicalScriptListPage";
import { RoleTrainingPlanDetailPage } from "./pages/RoleTrainingPlanDetailPage";
import { RoleTrainingPlanListPage } from "./pages/RoleTrainingPlanListPage";

export function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lesson-plans/generate" element={<LessonPlanGeneratePage />} />
          <Route path="/lesson-plans" element={<LessonPlanListPage />} />
          <Route path="/lesson-plans/:lessonPlanId" element={<LessonPlanDetailPage />} />
          <Route path="/musical-scripts/generate" element={<MusicalScriptGeneratePage />} />
          <Route path="/musical-scripts" element={<MusicalScriptListPage />} />
          <Route path="/musical-scripts/:musicalScriptId" element={<MusicalScriptDetailPage />} />
          <Route path="/role-training-plans" element={<RoleTrainingPlanListPage />} />
          <Route path="/role-training-plans/:roleTrainingPlanId" element={<RoleTrainingPlanDetailPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
