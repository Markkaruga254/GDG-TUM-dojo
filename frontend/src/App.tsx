import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, useEffect, useRef } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router";

import { RequireAdmin, RequireAuth } from "@/components/common/guards";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api";
import { HomePage } from "@/pages/home";
import { NotFoundPage } from "@/pages/not-found";

/* Route-level code splitting: everything except the landing page and the
 * 404 loads on demand. Suspense lives in AppShell so the navbar and footer
 * stay mounted while a chunk loads. */
const AuthCallbackPage = lazy(() =>
  import("@/pages/auth-callback").then((module) => ({ default: module.AuthCallbackPage })),
);
const BadgesPage = lazy(() =>
  import("@/pages/badges").then((module) => ({ default: module.BadgesPage })),
);
const ChallengeDetailPage = lazy(() =>
  import("@/pages/challenge-detail").then((module) => ({ default: module.ChallengeDetailPage })),
);
const ChallengeSubmitPage = lazy(() =>
  import("@/pages/challenge-submit").then((module) => ({ default: module.ChallengeSubmitPage })),
);
const ChallengesPage = lazy(() =>
  import("@/pages/challenges").then((module) => ({ default: module.ChallengesPage })),
);
const LeaderboardPage = lazy(() =>
  import("@/pages/leaderboard").then((module) => ({ default: module.LeaderboardPage })),
);
const ProfilePage = lazy(() =>
  import("@/pages/profile").then((module) => ({ default: module.ProfilePage })),
);
const SettingsPage = lazy(() =>
  import("@/pages/settings").then((module) => ({ default: module.SettingsPage })),
);
const SubmissionDetailPage = lazy(() =>
  import("@/pages/submission-detail").then((module) => ({ default: module.SubmissionDetailPage })),
);
const SubmissionsPage = lazy(() =>
  import("@/pages/submissions").then((module) => ({ default: module.SubmissionsPage })),
);
const StaffAuditPage = lazy(() =>
  import("@/pages/staff/audit").then((module) => ({ default: module.StaffAuditPage })),
);
const StaffBadgesPage = lazy(() =>
  import("@/pages/staff/badges").then((module) => ({ default: module.StaffBadgesPage })),
);
const ChallengeFormPage = lazy(() =>
  import("@/pages/staff/challenge-form").then((module) => ({ default: module.ChallengeFormPage })),
);
const StaffChallengesPage = lazy(() =>
  import("@/pages/staff/challenges").then((module) => ({ default: module.StaffChallengesPage })),
);
const StaffLayout = lazy(() =>
  import("@/pages/staff/staff-layout").then((module) => ({ default: module.StaffLayout })),
);
const StaffModerationPage = lazy(() =>
  import("@/pages/staff/moderation").then((module) => ({ default: module.StaffModerationPage })),
);
const StaffOverviewPage = lazy(() =>
  import("@/pages/staff/overview").then((module) => ({ default: module.StaffOverviewPage })),
);
const StaffUsersPage = lazy(() =>
  import("@/pages/staff/users").then((module) => ({ default: module.StaffUsersPage })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 20_000,
      retry: (failureCount, error) => {
        // Never retry client errors (auth, validation, not found).
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

function ScrollToTop() {
  const { pathname } = useLocation();
  const previous = useRef(pathname);
  useEffect(() => {
    if (previous.current !== pathname) {
      previous.current = pathname;
      window.scrollTo({ top: 0 });
    }
  }, [pathname]);
  return null;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TooltipProvider>
          <ScrollToTop />
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<HomePage />} />
              <Route path="challenges" element={<ChallengesPage />} />
              <Route path="challenges/:slug" element={<ChallengeDetailPage />} />
              <Route
                path="challenges/:slug/submit"
                element={
                  <RequireAuth message="Sign in with GitHub to submit a repository for this challenge.">
                    <ChallengeSubmitPage />
                  </RequireAuth>
                }
              />
              <Route
                path="submissions"
                element={
                  <RequireAuth message="Sign in to see your submissions and evaluation results.">
                    <SubmissionsPage />
                  </RequireAuth>
                }
              />
              <Route
                path="submissions/:id"
                element={
                  <RequireAuth message="Sign in to view this evaluation.">
                    <SubmissionDetailPage />
                  </RequireAuth>
                }
              />
              <Route path="leaderboard" element={<LeaderboardPage />} />
              <Route path="badges" element={<BadgesPage />} />
              <Route path="u/:username" element={<ProfilePage />} />
              <Route
                path="settings"
                element={
                  <RequireAuth message="Sign in to manage your profile and session.">
                    <SettingsPage />
                  </RequireAuth>
                }
              />
              <Route path="auth/callback" element={<AuthCallbackPage />} />

              <Route path="staff" element={<StaffLayout />}>
                <Route index element={<StaffOverviewPage />} />
                <Route path="challenges" element={<StaffChallengesPage />} />
                <Route path="challenges/new" element={<ChallengeFormPage key="create" />} />
                <Route path="challenges/:slug/edit" element={<ChallengeFormPage key="edit" />} />
                <Route path="submissions" element={<StaffModerationPage />} />
                <Route path="users" element={<StaffUsersPage />} />
                <Route path="badges" element={<StaffBadgesPage />} />
                <Route
                  path="audit"
                  element={
                    <RequireAdmin>
                      <StaffAuditPage />
                    </RequireAdmin>
                  }
                />
              </Route>

              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
          <Toaster />
        </TooltipProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
