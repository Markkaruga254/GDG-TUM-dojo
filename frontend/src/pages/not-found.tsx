import { Compass } from "lucide-react";
import { Link } from "react-router";

import { LogoMark } from "@/components/common/logo";
import { buttonClasses } from "@/components/ui/button";
import { PageContainer } from "@/components/layout/page-container";
import { usePageTitle } from "@/hooks/use-page-title";

export function NotFoundPage() {
  usePageTitle("Page not found");
  return (
    <PageContainer className="flex min-h-[60vh] items-center justify-center py-16">
      <div className="text-center">
        <LogoMark className="mx-auto size-12" />
        <p className="mt-6 font-mono text-sm text-faint">404</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          This page is not in the arena
        </h1>
        <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
          The link may be broken, or the page may have been moved.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link to="/" className={buttonClasses()}>
            <Compass aria-hidden />
            Back to home
          </Link>
          <Link to="/challenges" className={buttonClasses({ variant: "secondary" })}>
            Browse challenges
          </Link>
        </div>
      </div>
    </PageContainer>
  );
}
