import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type ProgressTone = "primary" | "success" | "warning" | "danger" | "accent";

const toneVar: Record<ProgressTone, string> = {
  primary: "var(--ba-primary)",
  success: "var(--ba-success)",
  warning: "var(--ba-warning)",
  danger: "var(--ba-danger)",
  accent: "var(--ba-accent)",
};

export interface ProgressRingProps {
  /** Current value (e.g. points awarded). */
  value: number;
  /** Maximum value (e.g. challenge max points). */
  max: number;
  size?: number;
  strokeWidth?: number;
  tone?: ProgressTone;
  className?: string;
  children?: ReactNode;
}

/** Circular score gauge used on evaluation results. */
export function ProgressRing({
  value,
  max,
  size = 132,
  strokeWidth = 10,
  tone = "primary",
  className,
  children,
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${value} of ${max} points`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--ba-surface-3)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={toneVar[tone]}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - ratio)}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22, 0.7, 0.3, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}
