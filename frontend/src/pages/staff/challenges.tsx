import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Archive, ArchiveRestore, ExternalLink, Pencil, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { toast } from "sonner";

import { archiveChallenge, publishChallenge } from "@/api/challenges";
import type { ChallengeSummary } from "@/api/types";
import { ChallengeStatusBadge, DifficultyBadge, TrackChip } from "@/components/domain/indicators";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button, buttonClasses } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Input, Select } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useUrlSearchInput } from "@/hooks/use-url-search";
import { useChallenges } from "@/hooks/queries";
import { qk } from "@/lib/query-keys";
import { formatDate, formatNumber } from "@/lib/utils";

export function StaffChallengesPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const status = params.get("status") ?? "";
  const search = params.get("q") ?? "";

  const [searchInput, setSearchInput] = useUrlSearchInput("q");

  const challengesQuery = useChallenges({
    page,
    page_size: 15,
    status: status || undefined,
    search: search || undefined,
  });

  const [archiveTarget, setArchiveTarget] = useState<ChallengeSummary | null>(null);

  const publishMutation = useMutation({
    mutationFn: (challengeId: string) => publishChallenge(challengeId),
    onSuccess: (challenge) => {
      void queryClient.invalidateQueries({ queryKey: qk.challenges.all });
      toast.success(`"${challenge.title}" published.`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Publish failed."),
  });

  const archiveMutation = useMutation({
    mutationFn: (challengeId: string) => archiveChallenge(challengeId),
    onSuccess: (challenge) => {
      void queryClient.invalidateQueries({ queryKey: qk.challenges.all });
      toast.success(`"${challenge.title}" archived.`);
      setArchiveTarget(null);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Archive failed."),
  });

  const data = challengesQuery.data;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 gap-3">
          <div className="relative max-w-xs flex-1">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-faint"
              aria-hidden
            />
            <Input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search challenges…"
              className="pl-9.5"
              aria-label="Search challenges"
            />
          </div>
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
            className="w-40"
          >
            <option value="">All statuses</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </Select>
        </div>
        <Link to="/staff/challenges/new" className={buttonClasses({ className: "shrink-0" })}>
          <Plus aria-hidden />
          New challenge
        </Link>
      </div>

      {challengesQuery.isError ? (
        <ErrorState error={challengesQuery.error} onRetry={() => challengesQuery.refetch()} />
      ) : challengesQuery.isPending ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <Card>
            <ul className="divide-y divide-line">
              {data.items.map((challenge) => (
                <li key={challenge.id} className="flex flex-col gap-3 px-5 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <ChallengeStatusBadge status={challenge.status} />
                    <TrackChip track={challenge.track} />
                    <DifficultyBadge difficulty={challenge.difficulty} />
                    <span className="ml-auto text-xs text-faint">
                      {formatNumber(challenge.max_points)} pts · created{" "}
                      {formatDate(challenge.created_at)}
                    </span>
                  </div>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <Link
                      to={`/challenges/${challenge.slug}`}
                      className="text-sm font-medium text-ink transition-colors hover:text-primary"
                    >
                      {challenge.title}
                    </Link>
                    <div className="flex flex-wrap items-center gap-2">
                      {challenge.status === "draft" ? (
                        <Button
                          size="sm"
                          loading={
                            publishMutation.isPending && publishMutation.variables === challenge.id
                          }
                          onClick={() => publishMutation.mutate(challenge.id)}
                        >
                          Publish
                        </Button>
                      ) : null}
                      {challenge.status === "published" ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setArchiveTarget(challenge)}
                        >
                          <Archive aria-hidden />
                          Archive
                        </Button>
                      ) : null}
                      {challenge.status === "archived" ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          loading={
                            publishMutation.isPending && publishMutation.variables === challenge.id
                          }
                          onClick={() => publishMutation.mutate(challenge.id)}
                        >
                          <ArchiveRestore aria-hidden />
                          Republish
                        </Button>
                      ) : null}
                      <Link
                        to={`/staff/challenges/${challenge.slug}/edit`}
                        className={buttonClasses({ variant: "secondary", size: "sm" })}
                      >
                        <Pencil aria-hidden />
                        Edit
                      </Link>
                      <Link
                        to={`/challenges/${challenge.slug}`}
                        className={buttonClasses({ variant: "ghost", size: "sm" })}
                      >
                        View
                        <ExternalLink aria-hidden />
                      </Link>
                    </div>
                  </div>
                </li>
              ))}
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
          title="No challenges found"
          description="Adjust the filters or create the first challenge."
          action={
            <Link to="/staff/challenges/new" className={buttonClasses()}>
              <Plus aria-hidden />
              New challenge
            </Link>
          }
        />
      )}

      <AlertDialog
        open={Boolean(archiveTarget)}
        onOpenChange={(open) => !open && setArchiveTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogTitle>Archive “{archiveTarget?.title}”?</AlertDialogTitle>
          <AlertDialogDescription>
            Archived challenges stay visible but stop accepting submissions. You can republish them
            later.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => archiveTarget && archiveMutation.mutate(archiveTarget.id)}
            >
              Archive
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
