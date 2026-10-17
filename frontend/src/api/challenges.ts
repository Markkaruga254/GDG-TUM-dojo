import { request } from "@/lib/api";

import type {
  ChallengeCreatePayload,
  ChallengeDetail,
  ChallengeListFilters,
  ChallengeSummary,
  ChallengeUpdatePayload,
  Page,
} from "./types";

function toQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function fetchChallenges(
  filters: ChallengeListFilters,
): Promise<Page<ChallengeSummary>> {
  const query = toQueryString({
    page: filters.page,
    page_size: filters.page_size,
    track: filters.track,
    difficulty: filters.difficulty,
    status: filters.status,
    search: filters.search,
    tag: filters.tag,
  });
  return request<Page<ChallengeSummary>>(`/api/v1/challenges${query}`);
}

export async function fetchChallenge(slug: string): Promise<ChallengeDetail> {
  return request<ChallengeDetail>(`/api/v1/challenges/${encodeURIComponent(slug)}`);
}

export async function createChallenge(payload: ChallengeCreatePayload): Promise<ChallengeDetail> {
  return request<ChallengeDetail>("/api/v1/challenges", { method: "POST", body: payload });
}

export async function updateChallenge(
  challengeId: string,
  payload: ChallengeUpdatePayload,
): Promise<ChallengeDetail> {
  return request<ChallengeDetail>(`/api/v1/challenges/${challengeId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function publishChallenge(challengeId: string): Promise<ChallengeDetail> {
  return request<ChallengeDetail>(`/api/v1/challenges/${challengeId}/publish`, {
    method: "POST",
  });
}

export async function archiveChallenge(challengeId: string): Promise<ChallengeDetail> {
  return request<ChallengeDetail>(`/api/v1/challenges/${challengeId}/archive`, {
    method: "POST",
  });
}
