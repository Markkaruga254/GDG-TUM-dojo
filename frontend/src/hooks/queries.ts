import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchAuditLogs, fetchAdminUsers, fetchChallengeSubmissions } from "@/api/admin";
import { fetchBadges, fetchUserBadges } from "@/api/badges";
import { fetchChallenge, fetchChallenges } from "@/api/challenges";
import { fetchLeaderboard, fetchMyLeaderboard } from "@/api/leaderboard";
import { fetchMySubmissions, fetchSubmission, fetchSubmissionResults } from "@/api/submissions";
import { fetchPortfolio, fetchProfile } from "@/api/users";
import { qk } from "@/lib/query-keys";

import type {
  AdminUserFilters,
  AuditLogFilters,
  ChallengeListFilters,
  MySubmissionFilters,
  SubmissionStatus,
} from "@/api/types";

/* --- challenges -------------------------------------------------------------- */

export function useChallenges(filters: ChallengeListFilters) {
  return useQuery({
    queryKey: qk.challenges.list(filters),
    queryFn: () => fetchChallenges(filters),
    placeholderData: keepPreviousData,
  });
}

export function useChallenge(slug: string | undefined) {
  return useQuery({
    queryKey: qk.challenges.detail(slug ?? ""),
    queryFn: () => fetchChallenge(slug as string),
    enabled: Boolean(slug),
    retry: false,
  });
}

/* --- submissions ---------------------------------------------------------------- */

const ACTIVE_SUBMISSION_STATUSES: SubmissionStatus[] = ["pending", "queued", "running"];

export function useMySubmissions(filters: MySubmissionFilters, enabled = true) {
  return useQuery({
    queryKey: qk.submissions.mine(filters),
    queryFn: () => fetchMySubmissions(filters),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useSubmission(submissionId: string | undefined) {
  return useQuery({
    queryKey: qk.submissions.detail(submissionId ?? ""),
    queryFn: () => fetchSubmission(submissionId as string),
    enabled: Boolean(submissionId),
    retry: false,
  });
}

/**
 * Evaluation results — automatically polls while the submission is still
 * being evaluated (e.g. after a queued evaluation on the server).
 */
export function useSubmissionResults(submissionId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.submissions.results(submissionId ?? ""),
    queryFn: () => fetchSubmissionResults(submissionId as string),
    enabled: Boolean(submissionId) && enabled,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.submission.status;
      return status && ACTIVE_SUBMISSION_STATUSES.includes(status) ? 2500 : false;
    },
  });
}

/* --- leaderboard -------------------------------------------------------------------- */

export function useLeaderboard(track: string | null, page: number, pageSize = 20) {
  return useQuery({
    queryKey: qk.leaderboard.list(track, page, pageSize),
    queryFn: () => fetchLeaderboard({ track, page, page_size: pageSize }),
    placeholderData: keepPreviousData,
  });
}

export function useMyLeaderboard(track: string | null, enabled = true) {
  return useQuery({
    queryKey: qk.leaderboard.me(track),
    queryFn: () => fetchMyLeaderboard(track),
    enabled,
    retry: false,
  });
}

/* --- badges ---------------------------------------------------------------------------- */

export function useBadges() {
  return useQuery({
    queryKey: qk.badges.catalogue,
    queryFn: () => fetchBadges(),
    staleTime: 5 * 60_000,
  });
}

export function useUserBadges(username: string | undefined) {
  return useQuery({
    queryKey: qk.badges.user(username ?? ""),
    queryFn: () => fetchUserBadges(username as string),
    enabled: Boolean(username),
    retry: false,
  });
}

/* --- profiles ----------------------------------------------------------------------------- */

export function useProfile(username: string | undefined) {
  return useQuery({
    queryKey: qk.profiles.profile(username ?? ""),
    queryFn: () => fetchProfile(username as string),
    enabled: Boolean(username),
    retry: false,
  });
}

export function usePortfolio(username: string | undefined) {
  return useQuery({
    queryKey: qk.profiles.portfolio(username ?? ""),
    queryFn: () => fetchPortfolio(username as string),
    enabled: Boolean(username),
    retry: false,
  });
}

/* --- staff ---------------------------------------------------------------------------------- */

export function useAdminUsers(filters: AdminUserFilters, enabled = true) {
  return useQuery({
    queryKey: qk.staff.users(filters),
    queryFn: () => fetchAdminUsers(filters),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useChallengeSubmissions(challengeId: string | undefined, page: number) {
  return useQuery({
    queryKey: qk.staff.submissions(challengeId ?? "", page, 20),
    queryFn: () => fetchChallengeSubmissions({ challenge_id: challengeId as string, page }),
    enabled: Boolean(challengeId),
    placeholderData: keepPreviousData,
  });
}

export function useAuditLogs(filters: AuditLogFilters, enabled = true) {
  return useQuery({
    queryKey: qk.staff.audit(filters),
    queryFn: () => fetchAuditLogs(filters),
    enabled,
    placeholderData: keepPreviousData,
  });
}
