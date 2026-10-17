import { useState } from "react";

import { avatarUrl, cn, initials } from "@/lib/utils";

export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";

const sizeClasses: Record<AvatarSize, string> = {
  xs: "size-5.5 text-[9px]",
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-14 text-lg",
  xl: "size-20 text-2xl",
};

export interface AvatarProps {
  user: {
    avatar_url: string | null;
    github_username: string;
    display_name?: string | null;
  };
  size?: AvatarSize;
  className?: string;
  /** Colored ring used for podium / highlight states. */
  ringClassName?: string;
}

export function Avatar({ user, size = "md", className, ringClassName }: AvatarProps) {
  const src = avatarUrl(user);
  // Track *which* source failed — a new src automatically resets the fallback.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const failed = failedSrc === src;

  const label = user.display_name?.trim() || user.github_username;
  const base = cn(
    "relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full",
    sizeClasses[size],
    ringClassName,
    className,
  );

  if (!src || failed) {
    return (
      <span
        className={cn(
          base,
          "bg-linear-to-br from-primary to-accent font-semibold text-white select-none",
        )}
        aria-label={label}
        role="img"
      >
        {initials(label) || "?"}
      </span>
    );
  }

  return (
    <span className={cn(base, "bg-surface-3")}>
      <img
        src={src}
        alt=""
        loading="lazy"
        className="size-full object-cover"
        onError={() => setFailedSrc(src)}
      />
    </span>
  );
}
