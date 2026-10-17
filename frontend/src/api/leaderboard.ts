import { request } from "@/lib/api";

import type { LeaderboardEntry, LeaderboardMe, Page } from "./types";

export async function fetchLeaderboard(params: {
  track?: string | null;
  page?: number;
  page_size?: number;
}): Promise<Page<LeaderboardEntry>> {
  const search = new URLSearchParams();
  if (params.track) search.set("track", params.track);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  const query = search.toString();
  return request<Page<LeaderboardEntry>>(`/api/v1/leaderboard${query ? `?${query}` : ""}`);
}

export async function fetchMyLeaderboard(track?: string | null): Promise<LeaderboardMe> {
  const search = new URLSearchParams();
  if (track) search.set("track", track);
  const query = search.toString();
  return request<LeaderboardMe>(`/api/v1/leaderboard/me${query ? `?${query}` : ""}`);
}
