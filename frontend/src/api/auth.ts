import { ApiError, apiUrl, request } from "@/lib/api";

import type { UserSelf } from "./types";

export interface LoginResponse {
  authorization_url: string;
  expires_in: number;
}

export interface LogoutResponse {
  status: string;
}

/** URL that starts the GitHub OAuth flow (browser navigation, not fetch). */
export function githubLoginUrl(): string {
  return apiUrl("/api/v1/auth/github/login");
}

export async function fetchLoginUrl(): Promise<LoginResponse> {
  return request<LoginResponse>("/api/v1/auth/github/login");
}

/** Current session user, or `null` when signed out (401 is a normal state). */
export async function fetchMe(signal?: AbortSignal): Promise<UserSelf | null> {
  try {
    return await request<UserSelf>("/api/v1/auth/me", { signal });
  } catch (error) {
    if (error instanceof ApiError && error.isUnauthorized) return null;
    throw error;
  }
}

export async function logout(): Promise<LogoutResponse> {
  return request<LogoutResponse>("/api/v1/auth/logout", { method: "POST" });
}
