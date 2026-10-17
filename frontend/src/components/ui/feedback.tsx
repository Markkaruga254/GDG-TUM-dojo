import {
  AlertTriangle,
  CheckCircle2,
  Inbox,
  Info,
  Loader2,
  OctagonAlert,
  RefreshCw,
} from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

import { Button } from "./button";

/* --- Spinner ------------------------------------------------------------------ */

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("size-4 animate-spin text-muted", className)} aria-hidden />;
}

/* --- EmptyState ------------------------------------------------------------------ */

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-line bg-surface/50 px-6 py-14 text-center",
        className,
      )}
    >
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-surface-2 text-faint">
        {icon ?? <Inbox className="size-5" aria-hidden />}
      </div>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {description ? <p className="mt-1 max-w-sm text-sm text-muted">{description}</p> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

/* --- ErrorState -------------------------------------------------------------------- */

export function errorMessageOf(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "network_error") return error.message;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export interface ErrorStateProps {
  error?: unknown;
  title?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  error,
  title = "Something went wrong",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-danger/30 bg-danger-soft/40 px-6 py-12 text-center",
        className,
      )}
    >
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-danger-soft text-danger">
        <AlertTriangle className="size-5" aria-hidden />
      </div>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted">{errorMessageOf(error)}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" className="mt-5" onClick={onRetry}>
          <RefreshCw aria-hidden />
          Try again
        </Button>
      ) : null}
    </div>
  );
}

/* --- Alert ---------------------------------------------------------------------------- */

export type AlertTone = "info" | "success" | "warning" | "danger";

const alertTones: Record<AlertTone, { wrap: string; icon: string }> = {
  info: { wrap: "border-primary/30 bg-primary-soft/60", icon: "text-primary" },
  success: { wrap: "border-success/30 bg-success-soft/60", icon: "text-success" },
  warning: { wrap: "border-warning/40 bg-warning-soft/60", icon: "text-warning" },
  danger: { wrap: "border-danger/30 bg-danger-soft/60", icon: "text-danger" },
};

const defaultIcons: Record<AlertTone, ReactNode> = {
  info: <Info aria-hidden />,
  success: <CheckCircle2 aria-hidden />,
  warning: <AlertTriangle aria-hidden />,
  danger: <OctagonAlert aria-hidden />,
};

export interface AlertProps extends ComponentProps<"div"> {
  tone?: AlertTone;
  icon?: ReactNode;
  title?: string;
}

export function Alert({ tone = "info", icon, title, className, children, ...props }: AlertProps) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-xl border p-4", alertTones[tone].wrap, className)}
      {...props}
    >
      <span className={cn("mt-0.5 shrink-0 [&_svg]:size-4.5", alertTones[tone].icon)}>
        {icon ?? defaultIcons[tone]}
      </span>
      <div className="min-w-0 text-sm">
        {title ? <p className="font-semibold text-ink">{title}</p> : null}
        <div className={cn("text-muted", title && "mt-0.5")}>{children}</div>
      </div>
    </div>
  );
}
