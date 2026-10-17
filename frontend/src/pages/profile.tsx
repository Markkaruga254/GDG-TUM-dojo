import { CalendarDays, ExternalLink, Pencil, Trophy } from "lucide-react";
import { Link, useParams } from "react-router";

import { GitHubIcon } from "@/components/common/github-icon";
import { BadgePill } from "@/components/domain/badge-tile";
import { DifficultyBadge, TrackChip } from "@/components/domain/indicators";
import { StatCard } from "@/components/domain/stat-card";
import { Avatar } from "@/components/ui/avatar";
import { buttonClasses } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/layout/page-container";
import { useSession } from "@/hooks/use-auth";
import { usePageTitle } from "@/hooks/use-page-title";
import { usePortfolio, useProfile, useUserBadges } from "@/hooks/queries";
import { displayNameOf, formatDate, formatNumber } from "@/lib/utils";

export function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const profileQuery = useProfile(username);
  const portfolioQuery = usePortfolio(username);
  const badgesQuery = useUserBadges(username);
  const { user: me } = useSession();

  const profile = profileQuery.data;
  usePageTitle(profile ? displayNameOf(profile.user) : "Profile");

  if (profileQuery.isPending) {
    return (
      <PageContainer className="py-10">
        <Skeleton className="h-56 w-full rounded-2xl" />
        <div className="mt-6 grid gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full rounded-xl" />
          ))}
        </div>
        <Skeleton className="mt-6 h-64 w-full rounded-xl" />
      </PageContainer>
    );
  }

  if (profileQuery.isError || !profile) {
    const notFound =
      profileQuery.error instanceof Error &&
      "status" in profileQuery.error &&
      (profileQuery.error as { status?: number }).status === 404;
    return (
      <PageContainer className="py-16">
        {notFound ? (
          <EmptyState
            title="Builder not found"
            description={`No profile exists for @${username ?? "unknown"}.`}
            action={
              <Link to="/leaderboard" className={buttonClasses({ variant: "secondary" })}>
                Back to the leaderboard
              </Link>
            }
          />
        ) : (
          <ErrorState error={profileQuery.error} onRetry={() => profileQuery.refetch()} />
        )}
      </PageContainer>
    );
  }

  const { user, stats } = profile;
  const isOwnProfile = me?.github_username === user.github_username;
  const badges = badgesQuery.data ?? [];
  const entries = portfolioQuery.data?.entries ?? [];

  return (
    <PageContainer className="animate-fade-in py-8 sm:py-10">
      <Card className="overflow-hidden">
        <div
          aria-hidden
          className="relative h-24 bg-linear-to-r from-primary/25 via-accent/20 to-primary/10"
        >
          <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(to_right,var(--ba-line)_1px,transparent_1px),linear-gradient(to_bottom,var(--ba-line)_1px,transparent_1px)] [background-size:32px_32px]" />
        </div>
        <CardContent className="-mt-10 pb-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="flex items-end gap-4">
              <Avatar user={user} size="xl" ringClassName="ring-4 ring-surface" />
              <div className="pb-1">
                <h1 className="text-xl font-semibold tracking-tight text-ink">
                  {displayNameOf(user)}
                </h1>
                <p className="text-sm text-faint">@{user.github_username}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={`https://github.com/${user.github_username}`}
                target="_blank"
                rel="noreferrer noopener"
                className={buttonClasses({ variant: "secondary", size: "sm" })}
              >
                <GitHubIcon aria-hidden />
                GitHub
                <ExternalLink className="size-3" aria-hidden />
              </a>
              {isOwnProfile ? (
                <Link to="/settings" className={buttonClasses({ size: "sm" })}>
                  <Pencil aria-hidden />
                  Edit profile
                </Link>
              ) : null}
            </div>
          </div>

          {user.bio ? <p className="mt-4 max-w-2xl text-sm text-muted">{user.bio}</p> : null}

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-faint">
            <span className="inline-flex items-center gap-1.5">
              <CalendarDays className="size-3.5" aria-hidden />
              Joined {formatDate(user.created_at)}
            </span>
          </div>

          {badges.length > 0 ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {badges.map((entry) => (
                <BadgePill key={entry.badge.id} entry={entry} />
              ))}
              <span className="text-xs text-faint">
                {badges.length} {badges.length === 1 ? "badge" : "badges"}
              </span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Trophy aria-hidden />}
          label="Points"
          value={formatNumber(stats.total_points)}
        />
        <StatCard label="Global rank" value={stats.global_rank ? `#${stats.global_rank}` : "—"} />
        <StatCard
          label="Challenges completed"
          value={formatNumber(stats.completed_challenges)}
          hint={`${formatNumber(stats.submissions_passed)} passed submissions`}
        />
        <StatCard label="Badges" value={formatNumber(stats.badges_count)} />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold tracking-tight text-ink">Portfolio</h2>
        <p className="mt-1 text-sm text-muted">
          Scored submissions that count toward the leaderboard.
        </p>

        <div className="mt-4">
          {portfolioQuery.isError ? (
            <ErrorState error={portfolioQuery.error} onRetry={() => portfolioQuery.refetch()} />
          ) : portfolioQuery.isPending ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-24 w-full rounded-xl" />
              ))}
            </div>
          ) : entries.length > 0 ? (
            <Card>
              <ul className="divide-y divide-line">
                {entries.map((entry) => (
                  <li
                    key={entry.submission_id}
                    className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <Link
                        to={`/challenges/${entry.challenge_slug}`}
                        className="text-sm font-medium text-ink transition-colors hover:text-primary"
                      >
                        {entry.challenge_title}
                      </Link>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2">
                        <TrackChip track={entry.track} />
                        <DifficultyBadge
                          difficulty={
                            entry.difficulty === "intermediate" || entry.difficulty === "advanced"
                              ? entry.difficulty
                              : "beginner"
                          }
                        />
                      </div>
                      <a
                        href={entry.repo_url}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="mt-1.5 inline-flex items-center gap-1.5 font-mono text-xs text-faint transition-colors hover:text-ink"
                      >
                        <GitHubIcon className="size-3.5" aria-hidden />
                        {entry.repo_full_name}
                        <ExternalLink className="size-3" aria-hidden />
                      </a>
                    </div>
                    <div className="flex shrink-0 items-center gap-6 sm:flex-col sm:items-end sm:gap-1">
                      <span className="text-sm font-semibold text-ink tabular-nums">
                        {formatNumber(entry.points)}
                        <span className="text-xs font-normal text-faint">
                          /{formatNumber(entry.max_points)} pts
                        </span>
                      </span>
                      <span className="text-xs text-faint">
                        {entry.achieved_at ? formatDate(entry.achieved_at) : "—"}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          ) : (
            <EmptyState
              title="No scored submissions yet"
              description={
                isOwnProfile
                  ? "Finish a challenge to start building your portfolio."
                  : "This builder has not landed points yet."
              }
            />
          )}
        </div>
      </div>
    </PageContainer>
  );
}
