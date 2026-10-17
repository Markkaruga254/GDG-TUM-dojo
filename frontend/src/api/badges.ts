import { request } from "@/lib/api";

import type { Badge, UserBadgeEntry } from "./types";

export async function fetchBadges(): Promise<Badge[]> {
  return request<Badge[]>("/api/v1/badges");
}

export async function fetchUserBadges(username: string): Promise<UserBadgeEntry[]> {
  return request<UserBadgeEntry[]>(`/api/v1/users/${encodeURIComponent(username)}/badges`);
}
