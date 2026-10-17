import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  Pencil,
  Send,
  Trophy,
} from "lucide-react";
import { Link, useParams } from "react-router";

import type { ChallengeDetail, CheckSummary } from "@/api/types";
import { SignInButton } from "@/components/common/sign-in-button";
import {
  ChallengeStatusBadge,
  DifficultyBadge,
  SubmissionStatusBadge,
  TrackChip,
} from "@/components/domain/indicators";
import { Alert, EmptyState, ErrorState } from "@/components/ui/feedback";
import { Badge } from "@/components/ui/badge";
import { buttonClasses } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useSession } from "@/hooks/use-auth";
import { useNow } from "@/hooks/use-now";
import { usePageTitle } from "@/hooks/use-page-title";
import { useChallenge, useMySubmissions } from "@/hooks/queries";
import { PageContainer } from "@/components/layout/page-container";
import { cn, describeDeadline, formatDate, formatDateTime, formatNumber } from "@/lib/utils";

function EvaluationChecklist({ checks, maxPoints }: { checks: CheckSummary[]; maxPoints: number }) {
  const enabled = checks.filter((check) => check.enabled);
  const allocated = enabled.reduce((total, check) => total + check.points, 0);

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>What the evaluator checks</CardTitle>
          <p className="mt-0.5 text-sm text-muted">
            {enabled.length} automated {enabled.length === 1 ? "check" : "checks"} ·{" "}
            {allocated < maxPoints
              ? `${formatNumber(allocated)} of ${formatNumber(maxPoints)} points allocated`
              : `${formatNumber(allocated)} points available`}
          </p>
        </div>
        <ClipboardList className="size-5 text-faint" aria-hidden />
      </CardHeader>
      <CardContent className="p-0">
        <ul className="divide-y divide-line">
          {checks.map((check) => (
            <li
              key={check.id}
              className={cn(
                "flex items-start justify-between gap-4 px-5 py-3.5",
                !check.enabled && "opacity-55",
              )}
            >
              <div className="min-w-0">
                <p className="text-sm text-ink">{check.description}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-faint">
                  <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono">{check.type}</code>
                  {check.required ? (
                    <span className="text-warning">Required</span>
                  ) : (
                    <span>Optional</span>
                  )}
                  {!check.enabled ? <span>Skipped</span> : null}
                </div>
              </div>
              <span className="shrink-0 text-sm font-semibold text-ink tabular-nums">
                {formatNumber(check.points)}
                <span className="ml-0.5 text-xs font-normal text-faint">pts</span>
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function SubmitPanel({ challenge }: { challenge: ChallengeDetail }) {
  const { user, isLoading: sessionLoading } = useSession();
  const mySubmissionsQuery = useMySubmissions(
    { challenge_id: challenge.id, page_size: 1 },
    Boolean(user),
  );

  const now = useNow();
  const notStarted = challenge.starts_at ? new Date(challenge.starts_at).getTime() > now : false;
  const ended = challenge.ends_at ? new Date(challenge.ends_at).getTime() <= now : false;
  const deadline = describeDeadline(challenge.ends_at, now);
  const isOpen = challenge.status === "published" && !notStarted && !ended;
  const latest = mySubmissionsQuery.data?.items[0];

  return (
    <Card className="lg:sticky lg:top-20">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-ink">
            <Trophy className="size-4.5 text-warning" aria-hidden />
            {formatNumber(challenge.max_points)} points
          </span>
          {deadline.tone === "soon" ? (
            <Badge tone="warning">{deadline.label}</Badge>
          ) : (
            <span className="text-xs text-faint">{deadline.label}</span>
          )}
        </div>

        <div className="mt-4 space-y-2 text-xs text-muted">
          <div className="flex items-center justify-between gap-3">
            <span>Opens</span>
            <span className="text-ink">
              {challenge.starts_at ? formatDate(challenge.starts_at) : "Now"}
            </span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span>Closes</span>
            <span className="text-ink">
              {challenge.ends_at ? formatDate(challenge.ends_at) : "Open ended"}
            </span>
          </div>
        </div>

        <div className="mt-5">
          {sessionLoading ? (
            <Skeleton className="h-11 w-full" />
          ) : !user ? (
            <div className="space-y-3">
              <SignInButton className="w-full" label="Sign in to submit" size="lg" />
              <p className="text-center text-xs text-faint">GitHub sign-in · takes a few seconds</p>
            </div>
          ) : !isOpen ? (
            <Alert tone="warning" title="Submissions are not open">
              {challenge.status !== "published"
                ? "This challenge is not published yet."
                : notStarted
                  ? "This challenge has not started yet."
                  : "This challenge has closed for submissions."}
            </Alert>
          ) : (
            <Link
              to={`/challenges/${challenge.slug}/submit`}
              className={buttonClasses({ size: "lg", className: "w-full" })}
            >
              <Send aria-hidden />
              Submit your repo
            </Link>
          )}
        </div>

        {latest ? (
          <div className="mt-5 rounded-lg border border-line bg-surface-2/60 p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-muted">Your latest submission</span>
              <SubmissionStatusBadge status={latest.status} />
            </div>
            <div className="mt-2 flex items-center justify-between gap-3 text-xs">
              <span className="truncate font-mono text-faint">{latest.repo_full_name}</span>
              <span className="shrink-0 text-muted tabular-nums">
                {latest.effective_points}/{challenge.max_points} pts
              </span>
            </div>
            <Link
              to={`/submissions/${latest.id}`}
              className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              View results
              <ExternalLink className="size-3" aria-hidden />
            </Link>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function ChallengeDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const challengeQuery = useChallenge(slug);
  const { isStaff } = useSession();
  const challenge = challengeQuery.data;

  usePageTitle(challenge?.title ?? "Challenge");

  if (challengeQuery.isPending) {
    return (
      <PageContainer className="py-8 sm:py-10">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="mt-6 h-9 w-2/3" />
        <Skeleton className="mt-3 h-5 w-1/3" />
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-56 w-full" />
          </div>
          <Skeleton className="h-72 w-full" />
        </div>
      </PageContainer>
    );
  }

  if (challengeQuery.isError || !challenge) {
    const notFound =
      challengeQuery.error instanceof Error &&
      "status" in challengeQuery.error &&
      (challengeQuery.error as { status?: number }).status === 404;
    return (
      <PageContainer className="py-16">
        {notFound ? (
          <EmptyState
            title="Challenge not found"
            description="This challenge may have been removed, or the link is incorrect."
            action={
              <Link to="/challenges" className={buttonClasses({ variant: "secondary" })}>
                Browse challenges
              </Link>
            }
          />
        ) : (
          <ErrorState error={challengeQuery.error} onRetry={() => challengeQuery.refetch()} />
        )}
      </PageContainer>
    );
  }

  return (
    <PageContainer className="animate-fade-in py-8 sm:py-10">
      <Link
        to="/challenges"
        className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        All challenges
      </Link>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <TrackChip track={challenge.track} />
        <DifficultyBadge difficulty={challenge.difficulty} />
        {isStaff ? <ChallengeStatusBadge status={challenge.status} /> : null}
      </div>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <h1 className="max-w-3xl text-2xl font-semibold tracking-tight text-balance text-ink sm:text-3xl">
          {challenge.title}
        </h1>
        {isStaff ? (
          <Link
            to={`/staff/challenges/${challenge.id}/edit`}
            className={buttonClasses({ variant: "secondary", size: "sm" })}
          >
            <Pencil aria-hidden />
            Edit
          </Link>
        ) : null}
      </div>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-faint">
        <span className="inline-flex items-center gap-1.5">
          <CalendarClock className="size-3.5" aria-hidden />
          Published {formatDateTime(challenge.created_at)}
        </span>
        {challenge.created_by ? <span>by @{challenge.created_by}</span> : null}
        {challenge.tags.map((tag) => (
          <Link
            key={tag}
            to={`/challenges?tag=${encodeURIComponent(tag)}`}
            className="rounded bg-surface-2 px-1.5 py-0.5 font-mono transition-colors hover:text-ink"
          >
            #{tag}
          </Link>
        ))}
      </div>

      <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-8">
          <section>
            <h2 className="text-base font-semibold text-ink">Brief</h2>
            <div className="mt-3 rounded-xl border border-line bg-surface p-5 text-sm leading-relaxed whitespace-pre-line text-muted">
              {challenge.description}
            </div>
          </section>

          {challenge.instructions.trim() ? (
            <section>
              <h2 className="text-base font-semibold text-ink">Instructions</h2>
              <div className="mt-3 rounded-xl border border-line bg-surface p-5 text-sm leading-relaxed whitespace-pre-line text-muted">
                {challenge.instructions}
              </div>
            </section>
          ) : null}

          {challenge.evaluation.length > 0 ? (
            <EvaluationChecklist checks={challenge.evaluation} maxPoints={challenge.max_points} />
          ) : null}

          <Alert tone="info" icon={<CheckCircle2 aria-hidden />}>
            Points are awarded per check. Required checks gate the submission — fail one and the run
            can still earn partial credit on the rest unless the challenge says otherwise.
          </Alert>
        </div>

        <div className="min-w-0">
          <SubmitPanel challenge={challenge} />
        </div>
      </div>
    </PageContainer>
  );
}
