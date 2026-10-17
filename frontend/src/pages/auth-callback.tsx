import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { toast } from "sonner";

import { fetchMe } from "@/api/auth";
import { SignInButton } from "@/components/common/sign-in-button";
import { LogoMark } from "@/components/common/logo";
import { buttonClasses } from "@/components/ui/button";
import { Spinner } from "@/components/ui/feedback";
import { PageContainer } from "@/components/layout/page-container";
import { usePageTitle } from "@/hooks/use-page-title";
import { qk } from "@/lib/query-keys";
import { displayNameOf } from "@/lib/utils";

function messageForCode(code: string | null): string {
  switch (code) {
    case "oauth_not_configured":
      return "GitHub sign-in is not configured on this server yet. An organizer needs to set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.";
    case "oauth_denied":
      return "The GitHub sign-in was cancelled.";
    case "oauth_missing_code":
      return "GitHub did not return a sign-in code. Please try again.";
    case "not_authenticated":
      return "The sign-in attempt expired or was interrupted. Please start again.";
    default:
      return `Sign-in failed${code ? ` (${code})` : ""}. Please try again.`;
  }
}

export function AuthCallbackPage() {
  usePageTitle("Signing in");
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const handled = useRef(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const status = params.get("status");
  const code = params.get("code");
  // Errors reported by the backend arrive in the URL — derive them directly
  // instead of copying into state; only fetch failures need state.
  const error = status !== "ok" ? messageForCode(code) : fetchError;

  useEffect(() => {
    if (handled.current || status !== "ok") return;
    handled.current = true;

    let cancelled = false;
    async function finish() {
      try {
        const me = await queryClient.fetchQuery({
          queryKey: qk.me,
          queryFn: ({ signal }) => fetchMe(signal),
        });
        if (cancelled) return;
        if (me) {
          toast.success(`Welcome, ${displayNameOf(me)}!`);
          navigate("/", { replace: true });
        } else {
          setFetchError(
            "Your session could not be established. Cookies may be blocked for this site.",
          );
        }
      } catch {
        if (!cancelled) {
          setFetchError("Could not reach the Build Arena API to confirm your session.");
        }
      }
    }
    void finish();
    return () => {
      cancelled = true;
    };
  }, [status, navigate, queryClient]);

  if (!error) {
    return (
      <PageContainer className="flex min-h-[60vh] flex-col items-center justify-center py-16 text-center">
        <LogoMark className="size-12 animate-pulse" />
        <div className="mt-6 flex items-center gap-2.5 text-sm text-muted">
          <Spinner />
          Completing GitHub sign-in…
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer className="flex min-h-[60vh] items-center justify-center py-16">
      <div className="w-full max-w-md rounded-2xl border border-line bg-surface px-8 py-12 text-center shadow-card">
        <LogoMark className="mx-auto size-12" />
        <h1 className="mt-5 text-lg font-semibold text-ink">Sign-in failed</h1>
        <p className="mt-2 text-sm text-muted">{error}</p>
        <div className="mt-6 flex flex-col items-center gap-3">
          <SignInButton size="lg" label="Try again" />
          <Link to="/" className={buttonClasses({ variant: "ghost", size: "sm" })}>
            Back to home
          </Link>
        </div>
      </div>
    </PageContainer>
  );
}
