import { useId } from "react";

import { cn } from "@/lib/utils";

/** Hexagon-and-bolt arena mark. */
export function LogoMark({ className }: { className?: string }) {
  const gradientId = useId();
  return (
    <svg viewBox="0 0 64 64" className={cn("size-7", className)} aria-hidden focusable="false">
      <defs>
        <linearGradient
          id={gradientId}
          x1="0"
          y1="0"
          x2="64"
          y2="64"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#4285f4" />
          <stop offset="1" stopColor="#7c4dff" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="14" fill={`url(#${gradientId})`} />
      <path
        d="M32 9.5 52 21v22L32 54.5 12 43V21Z"
        fill="none"
        stroke="#ffffff"
        strokeOpacity="0.55"
        strokeWidth="3.5"
        strokeLinejoin="round"
      />
      <path d="M36 17 23.5 36.5h7.2L28.5 47 41 27.5h-7.4Z" fill="#ffffff" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className="size-7" />
      <span className="flex flex-col leading-none">
        <span className="text-[15px] font-semibold tracking-tight text-ink">Build Arena</span>
        <span className="text-[10px] font-medium tracking-[0.14em] text-faint uppercase">
          GDG TUM
        </span>
      </span>
    </span>
  );
}
