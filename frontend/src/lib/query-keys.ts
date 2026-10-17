import type {
  AdminUserFilters,
  AuditLogFilters,
  ChallengeListFilters,
  MySubmissionFilters,
} from "@/api/types";

/**
 * Central react-query key factory. Keeping keys in one place makes
 * invalidation predictable across the app.
 */
export const qk = {
  me: ["me"] as const,

  challenges: {
    all: ["challenges"] as const,
    list: (filters: ChallengeListFilters) => ["challenges", "list", filters] as const,
    detail: (slug: string) => ["challenges", "detail", slug] as const,
  },

  submissions: {
    all: ["submissions"] as const,
    mine: (filters: MySubmissionFilters) => ["submissions", "mine", filters] as const,
    detail: (id: string) => ["submissions", "detail", id] as const,
    results: (id: string) => ["submissions", "results", id] as const,
  },

  leaderboard: {
    all: ["leaderboard"] as const,
    list: (track: string | null, page: number, pageSize: number) =>
      ["leaderboard", "list", { track, page, pageSize }] as const,
    me: (track: string | null) => ["leaderboard", "me", { track }] as const,
  },

  badges: {
    all: ["badges"] as const,
    catalogue: ["badges", "catalogue"] as const,
    user: (username: string) => ["badges", "user", username] as const,
  },

  profiles: {
    all: ["profiles"] as const,
    profile: (username: string) => ["profiles", username, "profile"] as const,
    portfolio: (username: string) => ["profiles", username, "portfolio"] as const,
  },

  staff: {
    users: (filters: AdminUserFilters) => ["staff", "users", filters] as const,
    submissions: (challengeId: string, page: number, pageSize: number) =>
      ["staff", "submissions", { challengeId, page, pageSize }] as const,
    audit: (filters: AuditLogFilters) => ["staff", "audit", filters] as const,
  },
} as const;
