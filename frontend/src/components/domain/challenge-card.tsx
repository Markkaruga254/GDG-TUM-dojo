import { Trophy } from "lucide-react";
import { Link } from "react-router";

import type { ChallengeSummary } from "@/api/types";
import { ChallengeStatusBadge, DifficultyBadge, TrackChip } from "@/components/domain/indicators";
import { cn, describeDeadline, formatNumber } from "@/lib/utils";

export interface ChallengeCardProps {
  challenge: ChallengeSummary;
  /** Staff viewers see draft/archived state on the card. */
  showStatus?: boolean;
  className?: string;
}

export function ChallengeCard({ challenge, showStatus = false, className }: ChallengeCardProps) {
  const deadline = describeDeadline(challenge.ends_at);
  const visibleTags = challenge.tags.slice(0, 3);
  const extraTags = challenge.tags.length - visibleTags.length;

  return (
    <Link
      to={`/challenges/${challenge.slug}`}
      className={cn(
        "group flex flex-col gap-4 rounded-xl border border-line bg-surface p-5 shadow-card transition-[border-color,transform,box-shadow] duration-200",
        "hover:-translate-y-0.5 hover:border-line-strong hover:shadow-pop",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <TrackChip track={challenge.track} />
          <DifficultyBadge difficulty={challenge.difficulty} />
        </div>
        {showStatus ? <ChallengeStatusBadge status={challenge.status} /> : null}
      </div>

      <div className="min-w-0">
        <h3 className="text-[15px] leading-snug font-semibold text-ink transition-colors group-hover:text-primary">
          {challenge.title}
        </h3>
        {visibleTags.length > 0 ? (
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            {visibleTags.map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-muted"
              >
                #{tag}
              </span>
            ))}
            {extraTags > 0 ? <span className="text-[11px] text-faint">+{extraTags}</span> : null}
          </div>
        ) : null}
      </div>

      <div className="mt-auto flex items-center justify-between gap-3 border-t border-line pt-3.5">
        <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink">
          <Trophy className="size-4 text-warning" aria-hidden />
          {formatNumber(challenge.max_points)}
          <span className="text-xs font-normal text-faint">pts</span>
        </span>
        <span
          className={cn(
            "text-xs",
            deadline.tone === "soon" && "font-medium text-warning",
            deadline.tone === "ended" && "text-faint",
            deadline.tone === "upcoming" && "text-muted",
            deadline.tone === "none" && "text-faint",
          )}
        >
          {deadline.label}
        </span>
      </div>
    </Link>
  );
}

export function ChallengeCardSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5">
      <div className="flex gap-2">
        <div className="h-6 w-20 animate-pulse rounded-full bg-surface-3" />
        <div className="h-6 w-24 animate-pulse rounded-full bg-surface-3" />
      </div>
      <div className="h-5 w-3/4 animate-pulse rounded-md bg-surface-3" />
      <div className="h-4 w-1/2 animate-pulse rounded-md bg-surface-3" />
      <div className="mt-2 flex justify-between border-t border-line pt-3.5">
        <div className="h-4 w-16 animate-pulse rounded-md bg-surface-3" />
        <div className="h-4 w-24 animate-pulse rounded-md bg-surface-3" />
      </div>
    </div>
  );
}
