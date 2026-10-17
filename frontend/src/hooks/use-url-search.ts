import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { useDebouncedValue } from "@/hooks/use-debounced-value";

/**
 * Two-way binding between a text input and a URL search param:
 *
 * - typing updates the input immediately
 * - the URL param follows after `delay` ms (shareable, refresh-safe links)
 * - external URL changes (back/forward, links) sync back into the input
 *
 * Returns the controlled input value and its setter. Read the committed
 * value from `useSearchParams()` where the query is built.
 */
export function useUrlSearchInput(paramKey = "q", delay = 350) {
  const [params, setParams] = useSearchParams();
  const urlValue = params.get(paramKey) ?? "";

  const [input, setInput] = useState(urlValue);
  const [syncedValue, setSyncedValue] = useState(urlValue);

  // Adjust state during render when the URL changed externally — the React
  // docs' recommended alternative to a sync effect. Also resets any pending
  // debounce so a back-navigation wins over an in-flight keystroke.
  if (urlValue !== syncedValue) {
    setSyncedValue(urlValue);
    setInput(urlValue);
  }

  const debounced = useDebouncedValue(input, delay);

  useEffect(() => {
    if (debounced === urlValue) return;
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (debounced) next.set(paramKey, debounced);
        else next.delete(paramKey);
        next.delete("page");
        return next;
      },
      { replace: true },
    );
  }, [debounced, urlValue, paramKey, setParams]);

  return [input, setInput] as const;
}
