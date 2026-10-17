import { ClipboardList, ExternalLink } from "lucide-react";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router";

import {
  DisqualifiedBadge,
  OverrideBadge,
  SubmissionStatusBadge,
} from "@/components/domain/indicators";
import { UserCell } from "@/components/domain/user-cell";
import { buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Select } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminUsers, useChallengeSubmissions, useChallenges } from "@/hooks/queries";
import { formatNumber, formatRelative } from "@/lib/utils";

export function StaffModerationPage() {
  const [params, setParams] = useSearchParams();
  const challengeId = params.get("challenge") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  const challengesQuery = useChallenges({ page_size: 100 });
  const usersQuery = useAdminUsers({ page_size: 100 });
  const submissionsQuery = useChallengeSubmissions(challengeId || undefined, page);

  const userMap = useMemo(() => {
    const map = new Map<
      string,
      { github_username: string; display_name: string | null; avatar_url: string | null }
    >();
    for (const user of usersQuery.data?.items ?? []) {
      map.set(user.id, {
        github_username: user.github_username,
        display_name: user.display_name,
        avatar_url: user.avatar_url,
      });
    }
    return map;
  }, [usersQuery.data]);

  const data = submissionsQuery.data;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted">
          Submissions are listed per challenge — pick one to review its queue.
        </p>
        <Select
          value={challengeId}
          onChange={(event) => {
            setParams(
              (previous) => {
                const next = new URLSearchParams(previous);
                if (event.target.value) next.set("challenge", event.target.value);
                else next.delete("challenge");
                next.delete("page");
                return next;
              },
              { replace: true },
            );
          }}
          aria-label="Select challenge"
          className="sm:w-80"
        >
          <option value="">Select a challenge…</option>
          {(challengesQuery.data?.items ?? []).map((challenge) => (
            <option key={challenge.id} value={challenge.id}>
              {challenge.title}
              {challenge.status !== "published" ? ` (${challenge.status})` : ""}
            </option>
          ))}
        </Select>
      </div>

      {!challengeId ? (
        <EmptyState
          icon={<ClipboardList className="size-5" aria-hidden />}
          title="Choose a challenge"
          description="Select a challenge above to see its submissions and moderation state."
        />
      ) : submissionsQuery.isError ? (
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
                const user = userMap.get(submission.user_id);
                return (
                  <li
                    key={submission.id}
                    className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
                      {user ? (
                        <UserCell user={user} className="sm:w-52" />
                      ) : (
                        <span className="font-mono text-xs text-faint">
                          {submission.user_id.slice(0, 8)}…
                        </span>
                      )}
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <SubmissionStatusBadge status={submission.status} />
                          {submission.is_disqualified ? <DisqualifiedBadge /> : null}
                          {submission.score_override_points !== null &&
                          !submission.is_disqualified ? (
                            <OverrideBadge points={submission.score_override_points} />
                          ) : null}
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-faint">
                          <span className="font-mono">{submission.repo_full_name}</span>
                          <span>{formatRelative(submission.submitted_at)}</span>
                          <span className="tabular-nums">
                            {formatNumber(submission.effective_points)} pts
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Link
                        to={`/submissions/${submission.id}`}
                        className={buttonClasses({ variant: "secondary", size: "sm" })}
                      >
                        Review
                        <ExternalLink aria-hidden />
                      </Link>
                    </div>
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
          />
        </>
      ) : (
        <EmptyState
          title="No submissions yet"
          description="Submissions for this challenge will appear here as students submit."
        />
      )}
    </div>
  );
}
