import { Link } from "react-router";

import { Avatar, type AvatarSize } from "@/components/ui/avatar";
import { cn, displayNameOf } from "@/lib/utils";

export interface UserCellProps {
  user: {
    github_username: string;
    display_name: string | null;
    avatar_url: string | null;
  };
  size?: AvatarSize;
  subtitle?: string;
  className?: string;
  /** Disable the profile link (e.g. inside a row that is already a link). */
  link?: boolean;
}

export function UserCell({ user, size = "sm", subtitle, className, link = true }: UserCellProps) {
  const name = displayNameOf(user);

  if (!link) {
    return (
      <span className={cn("flex min-w-0 items-center gap-2.5", className)}>
        <Avatar user={user} size={size} />
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium text-ink">{name}</span>
          <span className="block truncate text-xs text-faint">
            {subtitle ?? `@${user.github_username}`}
          </span>
        </span>
      </span>
    );
  }

  return (
    <Link
      to={`/u/${user.github_username}`}
      className={cn(
        "group flex min-w-0 items-center gap-2.5 rounded-lg transition-opacity hover:opacity-90",
        className,
      )}
    >
      <Avatar user={user} size={size} />
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-ink group-hover:text-primary">
          {name}
        </span>
        <span className="block truncate text-xs text-faint">
          {subtitle ?? `@${user.github_username}`}
        </span>
      </span>
    </Link>
  );
}
