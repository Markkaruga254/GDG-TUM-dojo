import { useEffect, useState } from "react";

/**
 * Ticking clock. Returns the current epoch time, refreshed every
 * `intervalMs` — keeps deadline maths out of render as an impure call.
 */
export function useNow(intervalMs = 60_000): number {
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);

  return now;
}
