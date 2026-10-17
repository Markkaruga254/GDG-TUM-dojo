import { ArrowRight, ClipboardCheck, Rocket, Sparkles, Trophy } from "lucide-react";
import { Link } from "react-router";

import { ChallengeCard, ChallengeCardSkeleton } from "@/components/domain/challenge-card";
import { BadgeTile, RankMedal } from "@/components/domain/badge-tile";
import { StatCard } from "@/components/domain/stat-card";
import { UserCell } from "@/components/domain/user-cell";
import { SignInButton } from "@/components/common/sign-in-button";
import { buttonClasses } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Skeleton } from "@/components/ui/skeleton";
import { useSession } from "@/hooks/use-auth";
import { useBadges, useChallenges, useLeaderboard } from "@/hooks/queries";
import { usePageTitle } from "@/hooks/use-page-title";
import { formatNumber } from "@/lib/utils";

function HeroAsideLeaderboard() {
  const boardQuery = useLeaderboard(null, 1, 5);

  return (
    <Card className="w-full max-w-sm">
      <CardHeader className="py-3.5">
        <CardTitle className="text-sm">Top builders</CardTitle>
        <span className="text-xs text-faint">
          {boardQuery.data ? `${formatNumber(boardQuery.data.total)} on the board` : "Live"}
        </span>
      </CardHeader>
      <CardContent className="p-2">
        {boardQuery.isPending ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="flex items-center gap-3 p-2">
                <Skeleton className="size-7 rounded-full" />
                <Skeleton className="h-8 flex-1" />
                <Skeleton className="h-4 w-12" />
              </div>
            ))}
          </div>
        ) : boardQuery.isError ? (
          <p className="p-4 text-sm text-muted">The board is taking a break. Try again soon.</p>
        ) : boardQuery.data.items.length === 0 ? (
          <div className="p-6 text-center">
            <Trophy className="mx-auto size-6 text-faint" aria-hidden />
            <p className="mt-2 text-sm text-muted">No scores yet — be the first on the board.</p>
          </div>
        ) : (
          <ul className="divide-y divide-line/70">
            {boardQuery.data.items.map((entry) => (
              <li key={entry.user_id} className="flex items-center gap-3 px-2 py-2.5">
                <RankMedal rank={entry.rank} className="size-6 shrink-0 text-[11px]" />
                <div className="min-w-0 flex-1">
                  <UserCell
                    user={{
                      github_username: entry.github_username,
                      display_name: entry.display_name,
                      avatar_url: entry.avatar_url,
                    }}
                    size="xs"
                    subtitle={`${entry.completed_challenges} completed`}
                  />
                </div>
                <span className="text-sm font-semibold text-ink tabular-nums">
                  {formatNumber(entry.total_points)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
      <CardFooter className="justify-center py-3">
        <Link
          to="/leaderboard"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          Full leaderboard
          <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </CardFooter>
    </Card>
  );
}

const STEPS = [
  {
    icon: ClipboardCheck,
    title: "Pick a challenge",
    body: "Every challenge has a clear brief and a published points breakdown — no hidden criteria.",
  },
  {
    icon: Rocket,
    title: "Submit your repository",
    body: "Link a GitHub repo and any supporting evidence. Submissions are rate-limited, so make them count.",
  },
  {
    icon: Sparkles,
    title: "Get scored automatically",
    body: "The evaluator inspects your repo against the checks and awards points instantly — then you climb the board.",
  },
];

export function HomePage() {
  usePageTitle();
  const { isAuthenticated } = useSession();

  const challengesQuery = useChallenges({ page_size: 6 });
  const boardQuery = useLeaderboard(null, 1, 5);
  const badgesQuery = useBadges();
  const featured = challengesQuery.data?.items ?? [];
  const badges = badgesQuery.data ?? [];

  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-line">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="animate-drift absolute -top-40 left-1/4 size-[28rem] rounded-full bg-primary/20 blur-3xl" />
          <div className="absolute -top-10 right-0 size-80 rounded-full bg-accent/15 blur-3xl" />
          <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(to_right,var(--ba-line)_1px,transparent_1px),linear-gradient(to_bottom,var(--ba-line)_1px,transparent_1px)] [background-size:56px_56px] [mask-image:radial-gradient(ellipse_70%_60%_at_50%_0%,black,transparent)]" />
        </div>
        <div className="relative mx-auto grid w-full max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_auto] lg:px-8 lg:py-24">
          <div className="animate-fade-up max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/80 px-3 py-1 text-xs font-medium text-muted backdrop-blur-sm">
              <span className="size-1.5 rounded-full bg-success" aria-hidden />
              GDG TUM · Build Arena
            </span>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-balance text-ink sm:text-5xl">
              Build. Ship. <span className="text-primary">Prove it.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-pretty text-muted sm:text-lg">
              Pick a challenge, push a real repository, and let automated evaluation turn your work
              into points. Clear rules, published weights, and a leaderboard that only counts
              evaluated work.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/challenges" className={buttonClasses({ size: "lg" })}>
                Browse challenges
                <ArrowRight aria-hidden />
              </Link>
              {isAuthenticated ? (
                <Link
                  to="/submissions"
                  className={buttonClasses({ variant: "secondary", size: "lg" })}
                >
                  My submissions
                </Link>
              ) : (
                <SignInButton size="lg" />
              )}
            </div>
          </div>
          <div className="animate-fade-up justify-self-center lg:justify-self-end [animation-delay:120ms]">
            <HeroAsideLeaderboard />
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            icon={<ClipboardCheck aria-hidden />}
            label="Open challenges"
            value={challengesQuery.data ? formatNumber(challengesQuery.data.total) : "—"}
          />
          <StatCard
            icon={<Trophy aria-hidden />}
            label="Builders on the board"
            value={boardQuery.data ? formatNumber(boardQuery.data.total) : "—"}
          />
          <StatCard
            icon={<Sparkles aria-hidden />}
            label="Badges to earn"
            value={badgesQuery.data ? formatNumber(badges.length) : "—"}
          />
        </div>
      </section>

      {/* Featured challenges */}
      <section className="mx-auto w-full max-w-6xl px-4 pb-14 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-ink">Open challenges</h2>
            <p className="mt-1 text-sm text-muted">Fresh briefs from the arena — find your fit.</p>
          </div>
          <Link
            to="/challenges"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            View all
            <ArrowRight className="size-3.5" aria-hidden />
          </Link>
        </div>
        {challengesQuery.isError ? (
          <ErrorState error={challengesQuery.error} onRetry={() => challengesQuery.refetch()} />
        ) : challengesQuery.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <ChallengeCardSkeleton key={index} />
            ))}
          </div>
        ) : featured.length === 0 ? (
          <EmptyState
            title="No challenges published yet"
            description="The organizers are preparing the first batch. Check back soon."
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((challenge) => (
              <ChallengeCard key={challenge.id} challenge={challenge} />
            ))}
          </div>
        )}
      </section>

      {/* How it works */}
      <section className="border-y border-line bg-bg-soft/60">
        <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
          <h2 className="text-xl font-semibold tracking-tight text-ink">How it works</h2>
          <p className="mt-1 text-sm text-muted">
            Three steps from a blank repository to a spot on the board.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {STEPS.map((step, index) => (
              <div
                key={step.title}
                className="rounded-xl border border-line bg-surface p-5 shadow-card"
              >
                <div className="flex items-center justify-between">
                  <span className="flex size-9 items-center justify-center rounded-lg bg-primary-soft text-primary">
                    <step.icon className="size-4.5" aria-hidden />
                  </span>
                  <span className="font-mono text-xs text-faint">0{index + 1}</span>
                </div>
                <h3 className="mt-4 text-sm font-semibold text-ink">{step.title}</h3>
                <p className="mt-1.5 text-sm text-muted">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Badges */}
      {badges.length > 0 ? (
        <section className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-ink">Badges</h2>
              <p className="mt-1 text-sm text-muted">
                Awarded automatically as you finish work on the platform.
              </p>
            </div>
            <Link
              to="/badges"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              All badges
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {badges.slice(0, 4).map((badge) => (
              <BadgeTile key={badge.id} badge={badge} />
            ))}
          </div>
        </section>
      ) : null}

      {/* CTA */}
      <section className="mx-auto w-full max-w-6xl px-4 pb-4 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-2xl border border-line bg-surface p-8 shadow-card sm:p-10">
          <div
            aria-hidden
            className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-primary/20 blur-3xl"
          />
          <div className="relative flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-ink">
                Ready to build something real?
              </h2>
              <p className="mt-1.5 max-w-xl text-sm text-muted">
                Sign in with GitHub, pick a challenge, and ship your first scored submission this
                week.
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {isAuthenticated ? (
                <Link to="/challenges" className={buttonClasses({ size: "lg" })}>
                  Find a challenge
                  <ArrowRight aria-hidden />
                </Link>
              ) : (
                <SignInButton size="lg" />
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
