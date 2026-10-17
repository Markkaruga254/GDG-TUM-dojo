import { Check } from "lucide-react";
import { useId } from "react";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface CheckboxProps extends Omit<ComponentProps<"input">, "type"> {
  label?: ReactNode;
}

export function Checkbox({ label, className, id, ...props }: CheckboxProps) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "group inline-flex cursor-pointer items-center gap-2.5 text-sm text-ink",
        props.disabled && "cursor-not-allowed opacity-50",
        className,
      )}
    >
      <span className="relative flex size-4.5 shrink-0 items-center justify-center">
        <input id={id} type="checkbox" className="peer sr-only" {...props} />
        <span
          aria-hidden
          className="absolute inset-0 rounded-[5px] border border-line-strong bg-surface transition-colors peer-checked:border-primary peer-checked:bg-primary peer-focus-visible:ring-2 peer-focus-visible:ring-primary/40"
        />
        <Check
          aria-hidden
          className="relative size-3 stroke-[3] text-primary-fg opacity-0 transition-opacity peer-checked:opacity-100"
        />
      </span>
      {label}
    </label>
  );
}

export interface SwitchProps extends Omit<ComponentProps<"button">, "onChange"> {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label?: ReactNode;
}

export function Switch({ checked, onCheckedChange, label, className, id, ...props }: SwitchProps) {
  // Associate the sibling <label> with the button so the switch always has an
  // accessible name — callers may omit an explicit id.
  const fallbackId = useId();
  const switchId = id ?? fallbackId;
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <button
        id={switchId}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          "relative h-5.5 w-10 shrink-0 rounded-full border transition-colors",
          checked ? "border-primary bg-primary" : "border-line-strong bg-surface-3",
        )}
        {...props}
      >
        <span
          aria-hidden
          className={cn(
            "absolute top-1/2 size-4 -translate-y-1/2 rounded-full bg-white shadow-sm transition-[left] duration-150",
            checked ? "left-[calc(100%-1.125rem)] bg-primary-fg" : "left-0.5",
          )}
        />
      </button>
      {label ? (
        <label htmlFor={switchId} className="cursor-pointer text-sm text-ink">
          {label}
        </label>
      ) : null}
    </div>
  );
}
