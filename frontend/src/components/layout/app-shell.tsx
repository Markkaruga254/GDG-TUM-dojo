import { Suspense } from "react";
import { Outlet } from "react-router";

import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Spinner } from "@/components/ui/feedback";

/**
 * Root layout: sticky navbar, routed content, footer.
 * Suspense keeps the chrome mounted while a route chunk loads.
 */
export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main-content"
        className="sr-only rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-fg focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50"
      >
        Skip to content
      </a>
      <Navbar />
      <main id="main-content" className="flex-1">
        <Suspense
          fallback={
            <div className="flex min-h-[55vh] items-center justify-center" role="status">
              <Spinner className="size-5" />
              <span className="sr-only">Loading page…</span>
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
