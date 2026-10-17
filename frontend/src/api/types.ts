/* ---------------------------------------------------------------------------
 * API types — kept in lock-step with the backend Pydantic schemas
 * (backend/app/schemas/*.py). Dates are ISO-8601 strings.
 * ------------------------------------------------------------------------ */

export type UserRole = "student" | "moderator" | "admin";
export type ChallengeStatus = "draft" | "published" | "archived";
export type Difficulty = "beginner" | "intermediate" | "advanced";
export type SubmissionStatus = "pending" | "queued" | "running" | "passed" | "failed" | "error";
export type EvaluationStatus = "running" | "completed" | "error";
export type CheckStatus = "passed" | "partial" | "failed" | "skipped" | "error";
export type BadgeRuleType =
  "submissions_finalized" | "challenges_passed" | "perfect_scores" | "track_challenges_passed";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/* --- users ---------------------------------------------------------------- */

export interface UserPublic {
  id: string;
  github_username: string;
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  created_at: string;
}

export interface UserSelf extends UserPublic {
  role: UserRole;
  is_active: boolean;
  updated_at: string;
}

export interface UserStats {
  total_points: number;
  completed_challenges: number;
  global_rank: number | null;
  badges_count: number;
  submissions_passed: number;
}

export interface UserProfile {
  user: UserPublic;
  stats: UserStats;
}

export interface PortfolioEntry {
  challenge_id: string;
  challenge_slug: string;
  challenge_title: string;
  track: string;
  difficulty: string;
  submission_id: string;
  repo_full_name: string;
  repo_url: string;
  points: number;
  max_points: number;
  achieved_at: string | null;
}

export interface UserPortfolio {
  user: UserPublic;
  stats: UserStats;
  entries: PortfolioEntry[];
}

export interface UserUpdatePayload {
  display_name?: string | null;
  bio?: string | null;
}

/* --- challenges ------------------------------------------------------------ */

export interface CheckSummary {
  id: string;
  type: string;
  description: string;
  points: number;
  required: boolean;
  enabled: boolean;
}

export interface ChallengeSummary {
  id: string;
  slug: string;
  title: string;
  track: string;
  difficulty: Difficulty;
  tags: string[];
  max_points: number;
  status: ChallengeStatus;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
}

export interface ChallengeDetail extends ChallengeSummary {
  description: string;
  instructions: string;
  created_by: string | null;
  evaluation: CheckSummary[];
}

export interface ChallengeListFilters {
  page?: number;
  page_size?: number;
  track?: string;
  difficulty?: string;
  status?: string;
  search?: string;
  tag?: string;
}

/** One evaluation check as configured (staff editor / API payload). */
export interface EvaluationCheck {
  id: string;
  type: string;
  description: string;
  points: number;
  required: boolean;
  enabled: boolean;
  params: Record<string, unknown>;
}

export interface EvaluationConfig {
  version: number;
  require_public_repo: boolean;
  checks: EvaluationCheck[];
}

export interface ChallengeCreatePayload {
  title: string;
  slug?: string;
  description: string;
  instructions?: string;
  track: string;
  difficulty: Difficulty;
  tags?: string[];
  max_points: number;
  starts_at?: string | null;
  ends_at?: string | null;
  evaluation_config: EvaluationConfig;
}

export type ChallengeUpdatePayload = Partial<Omit<ChallengeCreatePayload, "slug">> & {
  slug?: never;
};

/* --- submissions ----------------------------------------------------------- */

export interface SubmissionSummary {
  id: string;
  challenge_id: string;
  user_id: string;
  status: SubmissionStatus;
  repo_url: string;
  repo_full_name: string;
  points_awarded: number | null;
  effective_points: number;
  evaluation_summary: string | null;
  submitted_at: string;
  evaluated_at: string | null;
  evaluation_attempts: number;
  is_disqualified: boolean;
  disqualification_reason: string | null;
  score_override_points: number | null;
  score_override_reason: string | null;
}

export interface SubmissionDetail extends SubmissionSummary {
  notes: string | null;
  evidence_urls: string[];
}

export interface CheckResultOut {
  id: string;
  type: string;
  description: string;
  status: CheckStatus;
  max_points: number;
  awarded_points: number;
  message: string;
  required: boolean | null;
  evidence: Record<string, unknown>;
}

export interface EvaluationOut {
  id: string;
  status: EvaluationStatus;
  max_score: number;
  awarded_score: number;
  feedback: string | null;
  evaluator_version: string;
  started_at: string;
  completed_at: string | null;
  checks: CheckResultOut[];
}

export interface SubmissionResults {
  submission: SubmissionDetail;
  evaluation: EvaluationOut | null;
  challenge_slug: string;
  challenge_title: string;
  max_points: number;
  effective_points: number;
  counts_for_leaderboard: boolean;
}

export interface SubmissionCreatePayload {
  repo_url: string;
  notes?: string | null;
  evidence_urls?: string[];
}

export interface MySubmissionFilters {
  page?: number;
  page_size?: number;
  challenge_id?: string;
  status?: string;
}

/* --- leaderboard ------------------------------------------------------------ */

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  github_username: string;
  display_name: string | null;
  avatar_url: string | null;
  total_points: number;
  completed_challenges: number;
  achieved_at: string | null;
}

export interface LeaderboardChallengeEntry {
  challenge_id: string;
  challenge_slug: string;
  challenge_title: string;
  track: string;
  points: number;
  max_points: number;
  achieved_at: string | null;
}

export interface LeaderboardMe {
  rank: number | null;
  track: string | null;
  total_points: number;
  completed_challenges: number;
  achieved_at: string | null;
  entries: LeaderboardChallengeEntry[];
}

/* --- badges ------------------------------------------------------------------ */

export interface BadgeRule {
  type: BadgeRuleType;
  count: number;
  track: string | null;
}

export interface BadgeCriteria {
  description: string;
  rule: BadgeRule;
}

export interface Badge {
  id: string;
  slug: string;
  name: string;
  description: string;
  icon: string;
  criteria: BadgeCriteria;
}

export interface UserBadgeEntry {
  badge: Badge;
  awarded_at: string;
}

export interface BadgePayload {
  slug: string;
  name: string;
  description: string;
  icon: string;
  criteria: BadgeCriteria;
  is_active?: boolean;
}

export interface BadgeUpdatePayload {
  name?: string;
  description?: string;
  icon?: string;
  criteria?: BadgeCriteria;
  is_active?: boolean;
}

/* --- admin ------------------------------------------------------------------- */

export interface AdminUserSummary {
  id: string;
  github_username: string;
  display_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AdminUserFilters {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  actor_id: string | null;
  actor_username: string | null;
  target_type: string | null;
  target_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditLogFilters {
  page?: number;
  page_size?: number;
  action?: string;
  actor_id?: string;
}

export interface AdminActionResponse {
  status: string;
  message: string;
}
