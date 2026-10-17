import { useEffect } from "react";

const SUFFIX = "· Build Arena";

/** Keep the document title in sync with the current page. */
export function usePageTitle(title?: string): void {
  useEffect(() => {
    document.title = title ? `${title} ${SUFFIX}` : `Build Arena · GDG TUM`;
  }, [title]);
}
