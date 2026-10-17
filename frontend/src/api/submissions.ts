import { request } from "@/lib/api";

import type {
  MySubmissionFilters,
  Page,
  SubmissionCreatePayload,
  SubmissionDetail,
  SubmissionResults,
  SubmissionSummary,
} from "./types";

export async function createSubmission(
  challengeId: string,
  payload: SubmissionCreatePayload,
): Promise<SubmissionDetail> {
  return request<SubmissionDetail>(`/api/v1/challenges/${challengeId}/submissions`, {
    method: "POST",
    body: payload,
  });
}

export async function fetchMySubmissions(
  filters: MySubmissionFilters,
): Promise<Page<SubmissionSummary>> {
  const search = new URLSearchParams();
  if (filters.page) search.set("page", String(filters.page));
  if (filters.page_size) search.set("page_size", String(filters.page_size));
  if (filters.challenge_id) search.set("challenge_id", filters.challenge_id);
  if (filters.status) search.set("status", filters.status);
  const query = search.toString();
  return request<Page<SubmissionSummary>>(
    `/api/v1/users/me/submissions${query ? `?${query}` : ""}`,
  );
}

export async function fetchSubmission(submissionId: string): Promise<SubmissionDetail> {
  return request<SubmissionDetail>(`/api/v1/submissions/${submissionId}`);
}

export async function fetchSubmissionResults(submissionId: string): Promise<SubmissionResults> {
  return request<SubmissionResults>(`/api/v1/submissions/${submissionId}/results`);
}

/**
 * Trigger evaluation. The backend runs the evaluator synchronously for
 * pending submissions, so this call resolves with final results. A 202
 * response (returned as normal data) means an evaluation is already in
 * progress or the submission is already final — poll `/results` to catch up.
 */
export async function evaluateSubmission(
  submissionId: string,
  options: { force?: boolean } = {},
): Promise<SubmissionResults> {
  const query = options.force ? "?force=true" : "";
  return request<SubmissionResults>(`/api/v1/submissions/${submissionId}/evaluate${query}`, {
    method: "POST",
  });
}
