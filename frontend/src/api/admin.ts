import { request } from "@/lib/api";

import type {
  AdminActionResponse,
  AdminUserFilters,
  AdminUserSummary,
  AuditLogEntry,
  AuditLogFilters,
  Badge,
  BadgePayload,
  BadgeUpdatePayload,
  Page,
  SubmissionDetail,
  SubmissionSummary,
  UserRole,
} from "./types";

/* --- users ------------------------------------------------------------------ */

export async function fetchAdminUsers(filters: AdminUserFilters): Promise<Page<AdminUserSummary>> {
  const search = new URLSearchParams();
  if (filters.page) search.set("page", String(filters.page));
  if (filters.page_size) search.set("page_size", String(filters.page_size));
  if (filters.search) search.set("search", filters.search);
  if (filters.role) search.set("role", filters.role);
  if (filters.is_active !== undefined) search.set("is_active", String(filters.is_active));
  const query = search.toString();
  return request<Page<AdminUserSummary>>(`/api/v1/admin/users${query ? `?${query}` : ""}`);
}

export async function updateUserRole(
  userId: string,
  payload: { role: UserRole; reason?: string | null },
): Promise<AdminUserSummary> {
  return request<AdminUserSummary>(`/api/v1/admin/users/${userId}/role`, {
    method: "PATCH",
    body: payload,
  });
}

export async function updateUserStatus(
  userId: string,
  payload: { is_active: boolean; reason?: string | null },
): Promise<AdminUserSummary> {
  return request<AdminUserSummary>(`/api/v1/admin/users/${userId}/status`, {
    method: "PATCH",
    body: payload,
  });
}

/* --- submissions -------------------------------------------------------------- */

export async function fetchChallengeSubmissions(params: {
  challenge_id: string;
  page?: number;
  page_size?: number;
}): Promise<Page<SubmissionSummary>> {
  const search = new URLSearchParams({ challenge_id: params.challenge_id });
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  return request<Page<SubmissionSummary>>(`/api/v1/admin/submissions?${search.toString()}`);
}

export async function disqualifySubmission(
  submissionId: string,
  payload: { reason: string },
): Promise<SubmissionDetail> {
  return request<SubmissionDetail>(`/api/v1/admin/submissions/${submissionId}/disqualify`, {
    method: "POST",
    body: payload,
  });
}

export async function reinstateSubmission(submissionId: string): Promise<SubmissionDetail> {
  return request<SubmissionDetail>(`/api/v1/admin/submissions/${submissionId}/reinstate`, {
    method: "POST",
  });
}

export async function overrideSubmissionScore(
  submissionId: string,
  payload: { points: number; reason: string },
): Promise<SubmissionDetail> {
  return request<SubmissionDetail>(`/api/v1/admin/submissions/${submissionId}/score`, {
    method: "POST",
    body: payload,
  });
}

export async function clearSubmissionScoreOverride(
  submissionId: string,
): Promise<SubmissionDetail> {
  return request<SubmissionDetail>(`/api/v1/admin/submissions/${submissionId}/score-override`, {
    method: "DELETE",
  });
}

/* --- audit trail ------------------------------------------------------------------ */

export async function fetchAuditLogs(filters: AuditLogFilters): Promise<Page<AuditLogEntry>> {
  const search = new URLSearchParams();
  if (filters.page) search.set("page", String(filters.page));
  if (filters.page_size) search.set("page_size", String(filters.page_size));
  if (filters.action) search.set("action", filters.action);
  if (filters.actor_id) search.set("actor_id", filters.actor_id);
  const query = search.toString();
  return request<Page<AuditLogEntry>>(`/api/v1/admin/audit-logs${query ? `?${query}` : ""}`);
}

/* --- badges ----------------------------------------------------------------------- */

export async function createBadge(payload: BadgePayload): Promise<Badge> {
  return request<Badge>("/api/v1/admin/badges", { method: "POST", body: payload });
}

export async function updateBadge(badgeId: string, payload: BadgeUpdatePayload): Promise<Badge> {
  return request<Badge>(`/api/v1/admin/badges/${badgeId}`, { method: "PATCH", body: payload });
}

export async function grantBadge(
  userId: string,
  badgeSlug: string,
  payload: { reason?: string | null } = {},
): Promise<AdminActionResponse> {
  return request<AdminActionResponse>(
    `/api/v1/admin/users/${userId}/badges/${encodeURIComponent(badgeSlug)}`,
    { method: "POST", body: payload },
  );
}
