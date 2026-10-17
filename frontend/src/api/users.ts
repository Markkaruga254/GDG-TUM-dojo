import { request } from "@/lib/api";

import type { UserPortfolio, UserProfile, UserSelf, UserUpdatePayload } from "./types";

export async function fetchProfile(username: string): Promise<UserProfile> {
  return request<UserProfile>(`/api/v1/users/${encodeURIComponent(username)}/profile`);
}

export async function fetchPortfolio(username: string): Promise<UserPortfolio> {
  return request<UserPortfolio>(`/api/v1/users/${encodeURIComponent(username)}/portfolio`);
}

export async function updateMe(payload: UserUpdatePayload): Promise<UserSelf> {
  return request<UserSelf>("/api/v1/users/me", { method: "PATCH", body: payload });
}
