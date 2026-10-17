import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface StatCardProps {
  icon?: ReactNode;
  label: string;
  value: ReactNode;
  hint?: string;
  className?: string;
}

export function StatCard({ icon, label, value, hint, className }: StatCardProps) {
  return (
    <div className={cn("rounded-xl border border-line bg-surface p-4 shadow-card", className)}>
      <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-faint uppercase">
        {icon ? <span className="[&_svg]:size-3.5">{icon}</span> : null}
        {label}
      </div>
      <div className="mt-1.5 text-2xl font-semibold tracking-tight text-ink tabular-nums">
        {value}
      </div>
      {hint ? <div className="mt-0.5 text-xs text-muted">{hint}</div> : null}
    </div>
  );
}
