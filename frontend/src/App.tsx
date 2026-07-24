import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router";
import { AuthPageShell } from "./components/auth/AuthPageShell";
import { Shell } from "./components/layout/Shell";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LayoutPreferenceProvider } from "./contexts/LayoutPreferenceContext";
import { AccountPage } from "./pages/AccountPage";
import { AccountCreatePage } from "./pages/AccountCreatePage";
import { ClassInteractionDetailPage } from "./pages/ClassInteractionDetailPage";
import { ClassInteractionGeneratePage } from "./pages/ClassInteractionGeneratePage";
import { ClassInteractionListPage } from "./pages/ClassInteractionListPage";
import { HealthPage } from "./pages/HealthPage";
import { HomePage } from "./pages/HomePage";
import { LessonPlanDetailPage } from "./pages/LessonPlanDetailPage";
import { LessonPlanGeneratePage } from "./pages/LessonPlanGeneratePage";
import { LessonPlanListPage } from "./pages/LessonPlanListPage";
import { LessonPlanVariantGeneratePage } from "./pages/LessonPlanVariantGeneratePage";
import { LoginPage } from "./pages/LoginPage";
import { AudioCloneWorkbenchPage } from "./pages/AudioCloneWorkbenchPage";
import { ImageToImageWorkbenchPage } from "./pages/ImageToImageWorkbenchPage";
import { MediaStudioPage } from "./pages/MediaStudioPage";
import { MediaWorkbenchConfigPage } from "./pages/MediaWorkbenchConfigPage";
import { MotionTransferWorkbenchPage } from "./pages/MotionTransferWorkbenchPage";
import { VeoVideoWorkbenchPage } from "./pages/VeoVideoWorkbenchPage";
import { MovementGuideCreatePage } from "./pages/MovementGuideCreatePage";
import { MovementGuideDetailPage } from "./pages/MovementGuideDetailPage";
import { MovementGuideListPage } from "./pages/MovementGuideListPage";
import { MusicalFusionGeneratePage } from "./pages/MusicalFusionGeneratePage";
import { MusicalFusionPlanDetailPage } from "./pages/MusicalFusionPlanDetailPage";
import { MusicalFusionPlanListPage } from "./pages/MusicalFusionPlanListPage";
import { MusicalScriptDetailPage } from "./pages/MusicalScriptDetailPage";
import { MusicalScriptGeneratePage } from "./pages/MusicalScriptGeneratePage";
import { MusicalScriptListPage } from "./pages/MusicalScriptListPage";
import { PracticeSubmissionCreatePage } from "./pages/PracticeSubmissionCreatePage";
import { PracticeSubmissionDetailPage } from "./pages/PracticeSubmissionDetailPage";
import { PracticeSubmissionListPage } from "./pages/PracticeSubmissionListPage";
import { RehearsalReviewDetailPage } from "./pages/RehearsalReviewDetailPage";
import { RehearsalReviewGeneratePage } from "./pages/RehearsalReviewGeneratePage";
import { RehearsalReviewListPage } from "./pages/RehearsalReviewListPage";
import { RoleTrainingPlanDetailPage } from "./pages/RoleTrainingPlanDetailPage";
import { RoleTrainingGeneratePage } from "./pages/RoleTrainingGeneratePage";
import { RoleTrainingPlanListPage } from "./pages/RoleTrainingPlanListPage";
import { SongAdaptationDetailPage } from "./pages/SongAdaptationDetailPage";
import { SongAdaptationGeneratePage } from "./pages/SongAdaptationGeneratePage";
import { SongAdaptationListPage } from "./pages/SongAdaptationListPage";

function RequireAuth() {
  const { user, checkingSession } = useAuth();
  const location = useLocation();

  if (checkingSession) {
    return <AuthPageShell><div className="auth-form-heading"><p className="eyebrow">正在恢复会话</p><h2>请稍候</h2><p>正在向后端确认账号状态。</p></div></AuthPageShell>;
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <Outlet />;
}

function ProtectedShell() {
  return <Shell><Outlet /></Shell>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<Navigate to="/login" replace />} />
      <Route element={<RequireAuth />}>
        <Route element={<ProtectedShell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/accounts/new" element={<AccountCreatePage />} />
          <Route path="/media-studio" element={<MediaStudioPage />} />
          <Route path="/media-studio/audio-clone" element={<AudioCloneWorkbenchPage />} />
          <Route path="/media-studio/image-to-image" element={<ImageToImageWorkbenchPage />} />
          <Route path="/media-studio/veo" element={<VeoVideoWorkbenchPage />} />
          <Route path="/media-studio/motion-transfer" element={<MotionTransferWorkbenchPage />} />
          <Route path="/media-studio/configuration" element={<MediaWorkbenchConfigPage />} />
          <Route path="/lesson-plans/generate" element={<LessonPlanGeneratePage />} />
          <Route path="/lesson-plans" element={<LessonPlanListPage />} />
          <Route path="/lesson-plans/:lessonPlanId/variants/generate" element={<LessonPlanVariantGeneratePage />} />
          <Route path="/lesson-plans/:lessonPlanId" element={<LessonPlanDetailPage />} />
          <Route path="/interactions/generate" element={<ClassInteractionGeneratePage />} />
          <Route path="/interactions" element={<ClassInteractionListPage />} />
          <Route path="/interactions/:classInteractionId" element={<ClassInteractionDetailPage />} />
          <Route path="/musical-scripts/generate" element={<MusicalScriptGeneratePage />} />
          <Route path="/musical-scripts" element={<MusicalScriptListPage />} />
          <Route path="/musical-scripts/:musicalScriptId" element={<MusicalScriptDetailPage />} />
          <Route path="/song-adaptations/generate" element={<SongAdaptationGeneratePage />} />
          <Route path="/song-adaptations" element={<SongAdaptationListPage />} />
          <Route path="/song-adaptations/:songAdaptationId" element={<SongAdaptationDetailPage />} />
          <Route path="/musical-fusion-plans/generate" element={<MusicalFusionGeneratePage />} />
          <Route path="/musical-fusion-plans" element={<MusicalFusionPlanListPage />} />
          <Route path="/musical-fusion-plans/:musicalFusionPlanId" element={<MusicalFusionPlanDetailPage />} />
          <Route path="/role-training-plans/generate" element={<RoleTrainingGeneratePage />} />
          <Route path="/role-training-plans" element={<RoleTrainingPlanListPage />} />
          <Route path="/role-training-plans/:roleTrainingPlanId" element={<RoleTrainingPlanDetailPage />} />
          <Route path="/rehearsal-reviews/generate" element={<RehearsalReviewGeneratePage />} />
          <Route path="/rehearsal-reviews" element={<RehearsalReviewListPage />} />
          <Route path="/rehearsal-reviews/:rehearsalReviewId" element={<RehearsalReviewDetailPage />} />
          <Route path="/movement-guides/new" element={<MovementGuideCreatePage />} />
          <Route path="/movement-guides" element={<MovementGuideListPage />} />
          <Route path="/movement-guides/:movementGuideId" element={<MovementGuideDetailPage />} />
          <Route path="/practice-submissions/new" element={<PracticeSubmissionCreatePage />} />
          <Route path="/practice-submissions" element={<PracticeSubmissionListPage />} />
          <Route path="/practice-submissions/:submissionId" element={<PracticeSubmissionDetailPage />} />
          <Route path="/health" element={<HealthPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LayoutPreferenceProvider>
          <AppRoutes />
        </LayoutPreferenceProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
