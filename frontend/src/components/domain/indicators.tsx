import {
  AlertTriangle,
  Award,
  Calculator,
  CheckCircle2,
  CircleDashed,
  CircleX,
  Clock,
  Flame,
  Gauge,
  Hourglass,
  Loader2,
  MinusCircle,
  Rocket,
  ShieldBan,
  SkipForward,
  Star,
  Trophy,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Badge, type BadgeTone } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import type {
  ChallengeStatus,
  CheckStatus,
  Difficulty,
  SubmissionStatus,
  UserRole,
} from "@/api/types";

/* --- difficulty --------------------------------------------------------------- */

const difficultyTone: Record<Difficulty, BadgeTone> = {
  beginner: "success",
  intermediate: "warning",
  advanced: "danger",
};

const difficultyLabel: Record<Difficulty, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export function DifficultyBadge({
  difficulty,
  className,
}: {
  difficulty: Difficulty;
  className?: string;
}) {
  return (
    <Badge tone={difficultyTone[difficulty]} dot className={className}>
      {difficultyLabel[difficulty]}
    </Badge>
  );
}

/* --- track ----------------------------------------------------------------------- */

export function TrackChip({ track, className }: { track: string; className?: string }) {
  return (
    <Badge tone="outline" icon={<Gauge aria-hidden />} className={className}>
      {track}
    </Badge>
  );
}

/* --- challenge status -------------------------------------------------------------- */

const challengeStatusConfig: Record<
  ChallengeStatus,
  { tone: BadgeTone; label: string; icon: ReactNode }
> = {
  draft: { tone: "warning", label: "Draft", icon: <CircleDashed aria-hidden /> },
  published: { tone: "success", label: "Published", icon: <CheckCircle2 aria-hidden /> },
  archived: { tone: "neutral", label: "Archived", icon: <MinusCircle aria-hidden /> },
};

export function ChallengeStatusBadge({
  status,
  className,
}: {
  status: ChallengeStatus;
  className?: string;
}) {
  const config = challengeStatusConfig[status];
  return (
    <Badge tone={config.tone} icon={config.icon} className={className}>
      {config.label}
    </Badge>
  );
}

/* --- submission status --------------------------------------------------------------- */

const submissionStatusConfig: Record<
  SubmissionStatus,
  { tone: BadgeTone; label: string; icon: ReactNode }
> = {
  pending: { tone: "neutral", label: "Pending", icon: <Clock aria-hidden /> },
  queued: { tone: "neutral", label: "Queued", icon: <Hourglass aria-hidden /> },
  running: {
    tone: "primary",
    label: "Evaluating",
    icon: <Loader2 className="animate-spin" aria-hidden />,
  },
  passed: { tone: "success", label: "Passed", icon: <CheckCircle2 aria-hidden /> },
  failed: { tone: "danger", label: "Failed", icon: <CircleX aria-hidden /> },
  error: { tone: "danger", label: "Error", icon: <AlertTriangle aria-hidden /> },
};

export function SubmissionStatusBadge({
  status,
  className,
}: {
  status: SubmissionStatus;
  className?: string;
}) {
  const config = submissionStatusConfig[status];
  return (
    <Badge tone={config.tone} icon={config.icon} className={className}>
      {config.label}
    </Badge>
  );
}

export function DisqualifiedBadge({ className }: { className?: string }) {
  return (
    <Badge tone="danger" icon={<ShieldBan aria-hidden />} className={className}>
      Disqualified
    </Badge>
  );
}

export function OverrideBadge({ points, className }: { points: number; className?: string }) {
  return (
    <Badge tone="primary" icon={<Calculator aria-hidden />} className={className}>
      Override · {points} pts
    </Badge>
  );
}

/* --- evaluation check status ------------------------------------------------------------ */

const checkStatusConfig: Record<CheckStatus, { tone: BadgeTone; label: string; icon: ReactNode }> =
  {
    passed: { tone: "success", label: "Passed", icon: <CheckCircle2 aria-hidden /> },
    partial: { tone: "warning", label: "Partial", icon: <Gauge aria-hidden /> },
    failed: { tone: "danger", label: "Failed", icon: <CircleX aria-hidden /> },
    skipped: { tone: "neutral", label: "Skipped", icon: <SkipForward aria-hidden /> },
    error: { tone: "danger", label: "Error", icon: <AlertTriangle aria-hidden /> },
  };

export function CheckStatusBadge({
  status,
  className,
}: {
  status: CheckStatus;
  className?: string;
}) {
  const config = checkStatusConfig[status];
  return (
    <Badge tone={config.tone} icon={config.icon} className={className}>
      {config.label}
    </Badge>
  );
}

/* --- roles --------------------------------------------------------------------------------- */

const roleTone: Record<UserRole, BadgeTone> = {
  student: "neutral",
  moderator: "primary",
  admin: "accent",
};

export function RoleBadge({ role, className }: { role: UserRole; className?: string }) {
  return (
    <Badge tone={roleTone[role]} className={className}>
      {role}
    </Badge>
  );
}

/* --- badge catalogue icons -------------------------------------------------------------------- */

const badgeIconMap: Record<string, LucideIcon> = {
  rocket: Rocket,
  medal: Award,
  flame: Flame,
  trophy: Trophy,
  star: Star,
};

export function BadgeIcon({ icon, className }: { icon: string; className?: string }) {
  const Icon = badgeIconMap[icon.toLowerCase()] ?? Award;
  return <Icon className={cn("size-5", className)} aria-hidden />;
}
