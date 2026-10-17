import { ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const controlBase =
  "w-full rounded-lg border border-line bg-surface text-sm text-ink shadow-xs transition-[border-color,box-shadow,background-color] placeholder:text-faint hover:border-line-strong focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-faint";

export interface InputProps extends ComponentProps<"input"> {
  invalid?: boolean;
}

export function Input({ className, invalid, ...props }: InputProps) {
  return (
    <input
      className={cn(
        controlBase,
        "h-9.5 px-3",
        invalid && "border-danger hover:border-danger focus:border-danger focus:ring-danger/25",
        className,
      )}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}

export interface TextareaProps extends ComponentProps<"textarea"> {
  invalid?: boolean;
}

export function Textarea({ className, invalid, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn(
        controlBase,
        "min-h-24 px-3 py-2.5",
        invalid && "border-danger hover:border-danger focus:border-danger focus:ring-danger/25",
        className,
      )}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}

export function Select({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <div className={cn("relative", className)}>
      <select
        className={cn(controlBase, "h-9.5 cursor-pointer appearance-none pr-9 pl-3")}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-faint"
        aria-hidden
      />
    </div>
  );
}
