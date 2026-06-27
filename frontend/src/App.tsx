import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Shell } from "./components/layout/Shell";
import { HealthPage } from "./pages/HealthPage";
import { HomePage } from "./pages/HomePage";
import { LessonPlanDetailPage } from "./pages/LessonPlanDetailPage";
import { LessonPlanGeneratePage } from "./pages/LessonPlanGeneratePage";
import { LessonPlanListPage } from "./pages/LessonPlanListPage";

export function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lesson-plans/generate" element={<LessonPlanGeneratePage />} />
          <Route path="/lesson-plans" element={<LessonPlanListPage />} />
          <Route path="/lesson-plans/:lessonPlanId" element={<LessonPlanDetailPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
