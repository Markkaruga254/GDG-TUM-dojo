import { ScrollText, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Input, Select } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuditLogs } from "@/hooks/queries";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { formatDateTime } from "@/lib/utils";

/* Mirrors backend/app/services/audit.py::AuditAction */
const ACTION_OPTIONS = [
  { value: "challenge.create", label: "Challenge — create" },
  { value: "challenge.update", label: "Challenge — update" },
  { value: "challenge.publish", label: "Challenge — publish" },
  { value: "challenge.archive", label: "Challenge — archive" },
  { value: "user.role_change", label: "User — role change" },
  { value: "user.status_change", label: "User — status change" },
  { value: "submission.disqualify", label: "Submission — disqualify" },
  { value: "submission.reinstate", label: "Submission — reinstate" },
  { value: "submission.score_override", label: "Submission — score override" },
  { value: "submission.score_override_clear", label: "Submission — override cleared" },
  { value: "submission.force_evaluate", label: "Submission — force evaluate" },
  { value: "badge.create", label: "Badge — create" },
  { value: "badge.update", label: "Badge — update" },
  { value: "badge.grant", label: "Badge — grant" },
];

const ACTION_LABELS = new Map(ACTION_OPTIONS.map((option) => [option.value, option.label]));

export function StaffAuditPage() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const action = params.get("action") ?? "";

  const logsQuery = useAuditLogs({
    page,
    page_size: 20,
    action: action || undefined,
  });

  const [searchInput, setSearchInput] = useState("");
  const debouncedFilter = useDebouncedValue(searchInput, 300);

  // Free-text filter over the current page — useful when scanning for a username.
  const rows = (logsQuery.data?.items ?? []).filter((entry) => {
    if (!debouncedFilter) return true;
    const needle = debouncedFilter.toLowerCase();
    return (
      (entry.actor_username ?? "").toLowerCase().includes(needle) ||
      (entry.target_id ?? "").toLowerCase().includes(needle) ||
      entry.action.toLowerCase().includes(needle)
    );
  });

  useEffect(() => {
    const actionParam = params.get("action");
    if (actionParam && !ACTION_OPTIONS.some((option) => option.value === actionParam)) {
      setParams(
        (previous) => {
          const next = new URLSearchParams(previous);
          next.delete("action");
          return next;
        },
        { replace: true },
      );
    }
  }, [params, setParams]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Select
          value={action}
          onChange={(event) =>
            setParams(
              (previous) => {
                const next = new URLSearchParams(previous);
                if (event.target.value) next.set("action", event.target.value);
                else next.delete("action");
                next.delete("page");
                return next;
              },
              { replace: true },
            )
          }
          aria-label="Filter by action"
          className="sm:w-64"
        >
          <option value="">All actions</option>
          {ACTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <div className="relative max-w-xs flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-faint"
            aria-hidden
          />
          <Input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Filter this page…"
            className="pl-9.5"
            aria-label="Filter audit entries on this page"
          />
        </div>
      </div>

      {logsQuery.isError ? (
        <ErrorState error={logsQuery.error} onRetry={() => logsQuery.refetch()} />
      ) : logsQuery.isPending ? (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-14 w-full rounded-xl" />
          ))}
        </div>
      ) : rows.length > 0 ? (
        <>
          <Card>
            <ul className="divide-y divide-line">
              {rows.map((entry) => (
                <li key={entry.id} className="px-5 py-3.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-0.5">
                      <span className="text-sm font-medium text-ink">
                        {ACTION_LABELS.get(entry.action) ?? entry.action}
                      </span>
                      <span className="font-mono text-[11px] text-faint">{entry.action}</span>
                    </div>
                    <time className="text-xs text-faint" dateTime={entry.created_at}>
                      {formatDateTime(entry.created_at)}
                    </time>
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {entry.actor_username ? (
                      <>
                        by <span className="font-medium text-ink">@{entry.actor_username}</span>
                      </>
                    ) : (
                      "system"
                    )}
                    {entry.target_type ? (
                      <>
                        {" · "}
                        <span className="font-mono">
                          {entry.target_type}
                          {entry.target_id ? `:${entry.target_id}` : ""}
                        </span>
                      </>
                    ) : null}
                  </p>
                  {entry.metadata && Object.keys(entry.metadata).length > 0 ? (
                    <details className="group mt-2">
                      <summary className="cursor-pointer text-xs text-primary select-none hover:underline">
                        Details
                      </summary>
                      <pre className="mt-2 overflow-x-auto rounded-lg bg-surface-2 p-3 font-mono text-[11px] leading-relaxed text-muted">
                        {JSON.stringify(entry.metadata, null, 2)}
                      </pre>
                    </details>
                  ) : null}
                </li>
              ))}
            </ul>
          </Card>
          <Pagination
            page={logsQuery.data?.page ?? 1}
            pages={logsQuery.data?.pages ?? 1}
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
          icon={<ScrollText className="size-5" aria-hidden />}
          title="No audit entries"
          description={
            action || debouncedFilter
              ? "Nothing matches the current filters."
              : "Privileged actions will appear here as staff work on the platform."
          }
        />
      )}
    </div>
  );
}
