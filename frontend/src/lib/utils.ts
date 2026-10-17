import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes with conditional support. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const numberFormat = new Intl.NumberFormat("en-US");

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

const RELATIVE_STEPS: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
  ["second", 1],
];

/** "3 minutes ago", "in 2 days", … */
export function formatRelative(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "—";
  const deltaSeconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const abs = Math.abs(deltaSeconds);
  for (const [unit, seconds] of RELATIVE_STEPS) {
    if (abs >= seconds || unit === "second") {
      return relativeFormat.format(Math.round(deltaSeconds / seconds), unit);
    }
  }
  return "just now";
}

export type DeadlineTone = "none" | "upcoming" | "soon" | "ended";

export interface DeadlineInfo {
  label: string;
  tone: DeadlineTone;
}

/** Human-friendly deadline label for challenge cards. */
export function describeDeadline(
  endsAt: string | null | undefined,
  now = Date.now(),
): DeadlineInfo {
  if (!endsAt) return { label: "Open ended", tone: "none" };
  const diff = new Date(endsAt).getTime() - now;
  if (diff <= 0) return { label: "Submissions closed", tone: "ended" };
  const days = diff / 86_400_000;
  if (days < 2) {
    const hours = Math.max(1, Math.round(diff / 3_600_000));
    return { label: `Closes in ${hours}h`, tone: "soon" };
  }
  if (days < 14) {
    const rounded = Math.round(days);
    return { label: `Closes in ${rounded} ${rounded === 1 ? "day" : "days"}`, tone: "upcoming" };
  }
  return { label: `Closes ${formatDate(endsAt)}`, tone: "none" };
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural ?? `${singular}s`);
}

export function initials(name: string): string {
  return name
    .split(/[\s_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function avatarUrl(user: {
  avatar_url: string | null;
  github_username: string;
}): string | null {
  if (user.avatar_url) return user.avatar_url;
  if (user.github_username) return `https://github.com/${user.github_username}.png?size=160`;
  return null;
}

export function displayNameOf(user: {
  display_name: string | null;
  github_username: string;
}): string {
  return user.display_name?.trim() || user.github_username;
}
