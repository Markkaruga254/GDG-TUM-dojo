import { Crown, Trophy } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { RankMedal } from "@/components/domain/badge-tile";
import { UserCell } from "@/components/domain/user-cell";
import { Avatar } from "@/components/ui/avatar";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageContainer, PageHeader } from "@/components/layout/page-container";
import { useSession } from "@/hooks/use-auth";
import { usePageTitle } from "@/hooks/use-page-title";
import { useChallenges, useLeaderboard, useMyLeaderboard } from "@/hooks/queries";
import { cn, formatNumber, formatRelative } from "@/lib/utils";

import type { LeaderboardEntry } from "@/api/types";

function PodiumCard({ entry, place }: { entry: LeaderboardEntry; place: 1 | 2 | 3 }) {
  const ring =
    place === 1
      ? "ring-2 ring-warning/70"
      : place === 2
        ? "ring-2 ring-line-strong"
        : "ring-2 ring-danger/40";
  return (
    <Link
      to={`/u/${entry.github_username}`}
      className={cn(
        "flex flex-col items-center rounded-xl border bg-surface px-5 py-6 text-center shadow-card transition-[transform,border-color] hover:-translate-y-0.5",
        place === 1 ? "border-warning/40 sm:py-8" : "border-line",
      )}
    >
      <div className="relative">
        <Avatar
          user={{
            github_username: entry.github_username,
            display_name: entry.display_name,
            avatar_url: entry.avatar_url,
          }}
          size="lg"
          ringClassName={ring}
        />
        {place === 1 ? (
          <Crown
            className="absolute -top-4 left-1/2 size-5 -translate-x-1/2 text-warning"
            aria-hidden
          />
        ) : null}
      </div>
      <span className="mt-3 max-w-full truncate text-sm font-semibold text-ink">
        {entry.display_name?.trim() || entry.github_username}
      </span>
      <span className="text-xs text-faint">@{entry.github_username}</span>
      <span className="mt-2 text-lg font-semibold text-ink tabular-nums">
        {formatNumber(entry.total_points)}
        <span className="ml-1 text-xs font-normal text-faint">pts</span>
      </span>
      <span className="mt-0.5 text-xs text-muted">{entry.completed_challenges} completed</span>
    </Link>
  );
}

function MyStandingCard({ track }: { track: string | null }) {
  const meQuery = useMyLeaderboard(track);

  if (meQuery.isPending) return <Skeleton className="h-28 w-full rounded-xl" />;
  if (meQuery.isError || !meQuery.data) return null;
  const me = meQuery.data;

  return (
    <Card className="mb-6">
      <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <span className="flex size-11 items-center justify-center rounded-xl bg-primary-soft text-primary">
            <Trophy className="size-5" aria-hidden />
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">Your standing</p>
            <p className="text-sm text-muted">
              {me.rank
                ? `Rank #${me.rank}${track ? ` in ${track}` : ""} · ${me.completed_challenges} completed`
                : "You are not on the board yet — finish a challenge to appear."}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className="text-2xl font-semibold text-ink tabular-nums">
              {formatNumber(me.total_points)}
            </p>
            <p className="text-xs text-faint">points</p>
          </div>
          {!me.rank ? (
            <Link
              to="/challenges"
              className="text-sm font-medium text-primary whitespace-nowrap hover:underline"
            >
              Browse challenges
            </Link>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export function LeaderboardPage() {
  usePageTitle("Leaderboard");
  const { isAuthenticated, user } = useSession();
  const [params, setParams] = useSearchParams();
  const track = params.get("track") ?? "";
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  const boardQuery = useLeaderboard(track || null, page, 20);
  const facetsQuery = useChallenges({ page_size: 100 });
  const tracks = Array.from(
    new Set((facetsQuery.data?.items ?? []).map((challenge) => challenge.track)),
  ).sort((a, b) => a.localeCompare(b));

  const data = boardQuery.data;
  const podium = page === 1 ? (data?.items.slice(0, 3) ?? []) : [];

  function selectTrack(value: string) {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) next.set("track", value);
        else next.delete("track");
        next.delete("page");
        return next;
      },
      { replace: true },
    );
  }

  return (
    <PageContainer className="py-8 sm:py-10">
      <PageHeader
        title="Leaderboard"
        description="Points come from scored submissions — only finished, counted work appears here."
      />

      {tracks.length > 0 ? (
        <div className="mt-6 overflow-x-auto pb-1">
          <Tabs
            value={track || "overall"}
            onValueChange={(value) => selectTrack(value === "overall" ? "" : value)}
          >
            <TabsList>
              <TabsTrigger value="overall">Overall</TabsTrigger>
              {tracks.map((value) => (
                <TabsTrigger key={value} value={value}>
                  {value}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      ) : null}

      <div className="mt-6">
        {isAuthenticated ? <MyStandingCard track={track || null} /> : null}

        {boardQuery.isError ? (
          <ErrorState error={boardQuery.error} onRetry={() => boardQuery.refetch()} />
        ) : boardQuery.isPending ? (
          <div className="space-y-3">
            <Skeleton className="h-40 w-full rounded-xl" />
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-14 w-full rounded-xl" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <>
            {podium.length === 3 ? (
              <div className="mb-8 grid items-end gap-4 sm:grid-cols-3">
                <PodiumCard entry={podium[1] as LeaderboardEntry} place={2} />
                <PodiumCard entry={podium[0] as LeaderboardEntry} place={1} />
                <PodiumCard entry={podium[2] as LeaderboardEntry} place={3} />
              </div>
            ) : null}

            <Card>
              <ul className="divide-y divide-line">
                {data.items.map((entry) => {
                  const isMe = user?.github_username === entry.github_username;
                  return (
                    <li
                      key={entry.user_id}
                      className={cn(
                        "flex items-center gap-3 px-4 py-3 sm:gap-4 sm:px-5",
                        isMe && "bg-primary-soft/40",
                      )}
                    >
                      <RankMedal rank={entry.rank} />
                      <div className="min-w-0 flex-1">
                        <UserCell
                          user={{
                            github_username: entry.github_username,
                            display_name: entry.display_name,
                            avatar_url: entry.avatar_url,
                          }}
                          subtitle={`${entry.completed_challenges} completed`}
                        />
                      </div>
                      {entry.achieved_at ? (
                        <span className="hidden text-xs text-faint sm:block">
                          {formatRelative(entry.achieved_at)}
                        </span>
                      ) : null}
                      <span className="w-20 shrink-0 text-right text-sm font-semibold text-ink tabular-nums">
                        {formatNumber(entry.total_points)}
                        <span className="text-xs font-normal text-faint"> pts</span>
                      </span>
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
            icon={<Trophy className="size-5" aria-hidden />}
            title={track ? `No scores in ${track} yet` : "The board is empty"}
            description="Scores appear as soon as submissions pass evaluation. Be the first."
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
