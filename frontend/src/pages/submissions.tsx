import { useMemo } from "react";
import { ChevronRight, FileSearch } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import {
  SubmissionStatusBadge,
  OverrideBadge,
  DisqualifiedBadge,
} from "@/components/domain/indicators";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Select } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer, PageHeader } from "@/components/layout/page-container";
import { usePageTitle } from "@/hooks/use-page-title";
import { useChallenges, useMySubmissions } from "@/hooks/queries";
import { formatNumber, formatRelative } from "@/lib/utils";

const STATUS_OPTIONS = ["pending", "queued", "running", "passed", "failed", "error"] as const;

export function SubmissionsPage() {
  usePageTitle("My submissions");
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const status = params.get("status") ?? "";

  const submissionsQuery = useMySubmissions({
    page,
    page_size: 10,
    status: status || undefined,
  });

  // Challenge titles are resolved from the public challenge list.
  const challengesQuery = useChallenges({ page_size: 100 });
  const challengeMap = useMemo(() => {
    const map = new Map<string, { slug: string; title: string }>();
    for (const challenge of challengesQuery.data?.items ?? []) {
      map.set(challenge.id, { slug: challenge.slug, title: challenge.title });
    }
    return map;
  }, [challengesQuery.data]);

  const data = submissionsQuery.data;

  return (
    <PageContainer className="py-8 sm:py-10">
      <PageHeader
        title="My submissions"
        description="Every repository you have submitted, newest first."
        actions={
          <Select
            value={status}
            onChange={(event) => {
              setParams(
                (previous) => {
                  const next = new URLSearchParams(previous);
                  if (event.target.value) next.set("status", event.target.value);
                  else next.delete("status");
                  next.delete("page");
                  return next;
                },
                { replace: true },
              );
            }}
            aria-label="Filter by status"
            className="w-44"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {value[0]?.toUpperCase() + value.slice(1)}
              </option>
            ))}
          </Select>
        }
      />

      <div className="mt-6">
        {submissionsQuery.isError ? (
          <ErrorState error={submissionsQuery.error} onRetry={() => submissionsQuery.refetch()} />
        ) : submissionsQuery.isPending ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-20 w-full rounded-xl" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <>
            <Card>
              <ul className="divide-y divide-line">
                {data.items.map((submission) => {
                  const challenge = challengeMap.get(submission.challenge_id);
                  return (
                    <li key={submission.id}>
                      <Link
                        to={`/submissions/${submission.id}`}
                        className="grid grid-cols-[1fr_auto] items-center gap-4 px-4 py-4 transition-colors hover:bg-surface-2/60 sm:px-5"
                      >
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="truncate text-sm font-medium text-ink">
                              {challenge?.title ?? "Challenge"}
                            </span>
                            <SubmissionStatusBadge status={submission.status} />
                            {submission.is_disqualified ? <DisqualifiedBadge /> : null}
                            {submission.score_override_points !== null &&
                            !submission.is_disqualified ? (
                              <OverrideBadge points={submission.score_override_points} />
                            ) : null}
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-faint">
                            <span className="font-mono">{submission.repo_full_name}</span>
                            <span>Submitted {formatRelative(submission.submitted_at)}</span>
                            {submission.evaluation_attempts > 0 ? (
                              <span>
                                {submission.evaluation_attempts}{" "}
                                {submission.evaluation_attempts === 1 ? "run" : "runs"}
                              </span>
                            ) : null}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-ink tabular-nums">
                            {submission.evaluated_at ? (
                              <>
                                {formatNumber(submission.effective_points)}
                                <span className="text-xs font-normal text-faint"> pts</span>
                              </>
                            ) : (
                              <span className="text-faint" aria-label="Not scored yet">
                                —
                              </span>
                            )}
                          </span>
                          <ChevronRight className="size-4 text-faint" aria-hidden />
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </Card>
            <Pagination
              page={data.page}
              pages={data.pages}
              onPageChange={(next) =>
                setParams((previous) => {
                  const nextParams = new URLSearchParams(previous);
                  nextParams.set("page", String(next));
                  return nextParams;
                })
              }
              className="mt-6"
            />
          </>
        ) : (
          <EmptyState
            icon={<FileSearch className="size-5" aria-hidden />}
            title={status ? "No submissions with this status" : "No submissions yet"}
            description={
              status
                ? "Try a different status filter."
                : "Pick a challenge and submit your first repository — it only takes a minute."
            }
            action={
              <Link
                to="/challenges"
                className="inline-flex h-9.5 items-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-fg transition-colors hover:bg-primary-hover"
              >
                Browse challenges
              </Link>
            }
          />
        )}
      </div>
    </PageContainer>
  );
}
