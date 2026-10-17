import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

export type BadgeTone =
  "neutral" | "primary" | "accent" | "success" | "warning" | "danger" | "outline";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-surface-3 text-muted",
  primary: "bg-primary-soft text-primary",
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  outline: "border border-line text-muted",
};

export interface BadgeProps extends ComponentProps<"span"> {
  tone?: BadgeTone;
  dot?: boolean;
  icon?: ReactNode;
}

export function Badge({
  tone = "neutral",
  dot = false,
  icon,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        "[&_svg]:size-3.5 [&_svg]:shrink-0 [&_svg]:stroke-[2.5]",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {dot ? <span className="size-1.5 rounded-full bg-current" aria-hidden /> : null}
      {icon}
      {children}
    </span>
  );
}
