import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-[background-color,border-color,color,box-shadow,filter,translate] duration-150 active:translate-y-px disabled:pointer-events-none disabled:opacity-50 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-fg shadow-xs hover:bg-primary-hover",
        secondary:
          "border border-line bg-surface text-ink hover:border-line-strong hover:bg-surface-2",
        ghost: "text-muted hover:bg-surface-2 hover:text-ink",
        danger: "bg-danger text-danger-fg shadow-xs hover:brightness-105",
        "danger-ghost": "text-danger hover:bg-danger-soft",
        link: "h-auto p-0 text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 px-3 text-xs [&_svg]:size-3.5",
        md: "h-9.5 px-4 text-sm [&_svg]:size-4",
        lg: "h-11 px-5 text-sm [&_svg]:size-4",
        icon: "size-9 [&_svg]:size-4",
        "icon-sm": "size-7.5 rounded-md [&_svg]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export type ButtonVariant = NonNullable<VariantProps<typeof buttonVariants>["variant"]>;
export type ButtonSize = NonNullable<VariantProps<typeof buttonVariants>["size"]>;

export interface ButtonClassOptions extends VariantProps<typeof buttonVariants> {
  className?: string;
}

/** Compose button styles for non-button elements (e.g. react-router Links). */
export function buttonClasses({ variant, size, className }: ButtonClassOptions = {}): string {
  return cn(buttonVariants({ variant, size }), className);
}

export interface ButtonProps extends ComponentProps<"button">, VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export function Button({
  className,
  variant,
  size,
  loading = false,
  disabled,
  type,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type ?? "button"}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? <Loader2 className="animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
}
