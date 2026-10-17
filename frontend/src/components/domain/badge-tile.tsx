import type { Badge as BadgeType, UserBadgeEntry } from "@/api/types";
import { BadgeIcon } from "@/components/domain/indicators";
import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { cn, formatDate } from "@/lib/utils";

export interface BadgeTileProps {
  badge: BadgeType;
  awardedAt?: string | null;
  locked?: boolean;
  className?: string;
}

/** Badge catalogue tile — shown earned, or dimmed when not yet awarded. */
export function BadgeTile({ badge, awardedAt, locked = false, className }: BadgeTileProps) {
  return (
    <div
      className={cn(
        "flex gap-4 rounded-xl border border-line bg-surface p-4 shadow-card transition-colors",
        locked && "opacity-60",
        className,
      )}
    >
      <span
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-xl",
          locked ? "bg-surface-2 text-faint" : "bg-primary-soft text-primary",
        )}
      >
        <BadgeIcon icon={badge.icon} className="size-5.5" />
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-ink">{badge.name}</h3>
          {locked ? (
            <Badge tone="outline">Locked</Badge>
          ) : awardedAt ? (
            <Badge tone="success" dot>
              Earned
            </Badge>
          ) : null}
        </div>
        <p className="mt-1 text-sm text-muted">{badge.description}</p>
        <p className="mt-1.5 text-xs text-faint">
          {awardedAt
            ? `Awarded ${formatDate(awardedAt)}`
            : badge.criteria?.description
              ? `Criteria: ${badge.criteria.description}`
              : null}
        </p>
      </div>
    </div>
  );
}

/** Compact icon chip used next to names and in profile headers. */
export function BadgePill({ entry }: { entry: UserBadgeEntry }) {
  return (
    <Tooltip content={`${entry.badge.name} — ${entry.badge.description}`}>
      <span className="flex size-8 items-center justify-center rounded-full bg-primary-soft text-primary">
        <BadgeIcon icon={entry.badge.icon} className="size-4" />
      </span>
    </Tooltip>
  );
}

export function RankMedal({ rank, className }: { rank: number; className?: string }) {
  const styles =
    rank === 1
      ? "bg-warning-soft text-warning border-warning/40"
      : rank === 2
        ? "bg-surface-3 text-muted border-line-strong"
        : rank === 3
          ? "bg-danger-soft text-danger border-danger/30"
          : "bg-surface-2 text-faint border-line";
  return (
    <span
      className={cn(
        "inline-flex size-7 items-center justify-center rounded-full border text-xs font-bold tabular-nums",
        styles,
        className,
      )}
    >
      {rank}
    </span>
  );
}
