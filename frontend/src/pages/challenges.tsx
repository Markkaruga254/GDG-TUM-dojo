import { useCallback, useMemo } from "react";
import { Plus, Search, SlidersHorizontal, X } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { ChallengeCard, ChallengeCardSkeleton } from "@/components/domain/challenge-card";
import { buttonClasses } from "@/components/ui/button";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Input, Select } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { useSession } from "@/hooks/use-auth";
import { useUrlSearchInput } from "@/hooks/use-url-search";
import { usePageTitle } from "@/hooks/use-page-title";
import { useChallenges } from "@/hooks/queries";
import { PageContainer, PageHeader } from "@/components/layout/page-container";
import { pluralize } from "@/lib/utils";

const DIFFICULTIES = ["beginner", "intermediate", "advanced"] as const;
const STATUSES = ["draft", "published", "archived"] as const;

export function ChallengesPage() {
  usePageTitle("Challenges");
  const { isStaff } = useSession();
  const [params, setParams] = useSearchParams();

  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const search = params.get("q") ?? "";
  const track = params.get("track") ?? "";
  const difficulty = params.get("difficulty") ?? "";
  const status = params.get("status") ?? "";
  const tag = params.get("tag") ?? "";

  const [searchInput, setSearchInput] = useUrlSearchInput("q");

  const updateParams = useCallback(
    (patch: Record<string, string | null>) => {
      setParams(
        (previous) => {
          const next = new URLSearchParams(previous);
          for (const [key, value] of Object.entries(patch)) {
            if (value === null || value === "") next.delete(key);
            else next.set(key, value);
          }
          if (patch.page === undefined) next.delete("page");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  const filters = useMemo(
    () => ({
      page,
      page_size: 12,
      search: search || undefined,
      track: track || undefined,
      difficulty: difficulty || undefined,
      status: status || undefined,
      tag: tag || undefined,
    }),
    [page, search, track, difficulty, status, tag],
  );

  const challengesQuery = useChallenges(filters);
  // One broad fetch powers the track/tag filter options.
  const facetsQuery = useChallenges({ page_size: 100 });
  const facetItems = useMemo(() => facetsQuery.data?.items ?? [], [facetsQuery.data]);

  const tracks = useMemo(() => {
    const values = new Set<string>();
    for (const item of facetItems) values.add(item.track);
    if (track) values.add(track);
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [facetItems, track]);

  const tags = useMemo(() => {
    const values = new Set<string>();
    for (const item of facetItems) for (const value of item.tags) values.add(value);
    if (tag) values.add(tag);
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }, [facetItems, tag]);

  const hasFilters = Boolean(search || track || difficulty || status || tag);
  const data = challengesQuery.data;

  return (
    <PageContainer className="py-8 sm:py-10">
      <PageHeader
        title="Challenges"
        description="Every brief in the arena. Filter by track, difficulty, or tag."
        actions={
          isStaff ? (
            <Link to="/staff/challenges/new" className={buttonClasses({ size: "md" })}>
              <Plus aria-hidden />
              New challenge
            </Link>
          ) : null
        }
      />

      {/* Filter bar */}
      <div className="mt-6 rounded-xl border border-line bg-surface p-3.5 shadow-card sm:p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr_auto]">
          <div className="relative">
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
            value={track}
            onChange={(event) => updateParams({ track: event.target.value || null })}
            aria-label="Filter by track"
          >
            <option value="">All tracks</option>
            {tracks.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
          <Select
            value={difficulty}
            onChange={(event) => updateParams({ difficulty: event.target.value || null })}
            aria-label="Filter by difficulty"
          >
            <option value="">Any difficulty</option>
            {DIFFICULTIES.map((value) => (
              <option key={value} value={value}>
                {value[0]?.toUpperCase() + value.slice(1)}
              </option>
            ))}
          </Select>
          {isStaff ? (
            <Select
              value={status}
              onChange={(event) => updateParams({ status: event.target.value || null })}
              aria-label="Filter by status"
            >
              <option value="">All statuses</option>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {value[0]?.toUpperCase() + value.slice(1)}
                </option>
              ))}
            </Select>
          ) : (
            <Select
              value={tag}
              onChange={(event) => updateParams({ tag: event.target.value || null })}
              aria-label="Filter by tag"
            >
              <option value="">Any tag</option>
              {tags.map((value) => (
                <option key={value} value={value}>
                  #{value}
                </option>
              ))}
            </Select>
          )}
          <div className="flex items-center justify-end">
            {hasFilters ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  updateParams({ q: null, track: null, difficulty: null, status: null, tag: null })
                }
              >
                <X aria-hidden />
                Clear
              </Button>
            ) : (
              <span className="inline-flex items-center gap-1.5 pr-1 text-xs text-faint">
                <SlidersHorizontal className="size-3.5" aria-hidden />
                {data ? `${data.total} ${pluralize(data.total, "challenge")}` : "…"}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="mt-6">
        {challengesQuery.isError ? (
          <ErrorState error={challengesQuery.error} onRetry={() => challengesQuery.refetch()} />
        ) : challengesQuery.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <ChallengeCardSkeleton key={index} />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((challenge) => (
                <ChallengeCard key={challenge.id} challenge={challenge} showStatus={isStaff} />
              ))}
            </div>
            <Pagination
              page={data.page}
              pages={data.pages}
              onPageChange={(next) => {
                setParams((previous) => {
                  const nextParams = new URLSearchParams(previous);
                  nextParams.set("page", String(next));
                  return nextParams;
                });
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className="mt-8"
            />
          </>
        ) : (
          <EmptyState
            title={hasFilters ? "No challenges match" : "No challenges yet"}
            description={
              hasFilters
                ? "Try adjusting or clearing the filters."
                : "Challenges will appear here as soon as they are published."
            }
            action={
              hasFilters ? (
                <Button
                  variant="secondary"
                  onClick={() =>
                    updateParams({
                      q: null,
                      track: null,
                      difficulty: null,
                      status: null,
                      tag: null,
                    })
                  }
                >
                  Clear filters
                </Button>
              ) : null
            }
          />
        )}
      </div>
    </PageContainer>
  );
}
