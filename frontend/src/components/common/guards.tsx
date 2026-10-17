import { Loader2, ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { SignInButton } from "@/components/common/sign-in-button";
import { LogoMark } from "@/components/common/logo";
import { buttonClasses } from "@/components/ui/button";
import { useSession } from "@/hooks/use-auth";

export function PageLoading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-muted">
      <Loader2 className="size-6 animate-spin" aria-hidden />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function SignInPrompt({ message }: { message?: string }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center rounded-2xl border border-line bg-surface px-8 py-12 text-center shadow-card">
      <LogoMark className="size-12" />
      <h1 className="mt-5 text-lg font-semibold text-ink">Sign in to continue</h1>
      <p className="mt-2 text-sm text-muted">
        {message ??
          "Build Arena uses GitHub for sign-in — it also links the repositories you submit."}
      </p>
      <SignInButton className="mt-6" size="lg" />
    </div>
  );
}

export function ForbiddenState({ message }: { message?: string }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center rounded-2xl border border-line bg-surface px-8 py-12 text-center shadow-card">
      <span className="flex size-12 items-center justify-center rounded-full bg-danger-soft text-danger">
        <ShieldAlert className="size-6" aria-hidden />
      </span>
      <h1 className="mt-5 text-lg font-semibold text-ink">Access restricted</h1>
      <p className="mt-2 text-sm text-muted">
        {message ?? "This area is only available to moderators and admins."}
      </p>
      <Link to="/" className={buttonClasses({ variant: "secondary", className: "mt-6" })}>
        Back to home
      </Link>
    </div>
  );
}

/** Gate that requires an authenticated session. */
export function RequireAuth({ children, message }: { children: ReactNode; message?: string }) {
  const { user, isLoading } = useSession();
  if (isLoading) return <PageLoading label="Checking your session…" />;
  if (!user) return <SignInPrompt message={message} />;
  return <>{children}</>;
}

/** Gate that requires a moderator or admin role. */
export function RequireStaff({ children }: { children: ReactNode }) {
  const { user, isLoading, isStaff } = useSession();
  if (isLoading) return <PageLoading label="Checking your session…" />;
  if (!user) return <SignInPrompt message="Sign in with a staff account to open the console." />;
  if (!isStaff) return <ForbiddenState />;
  return <>{children}</>;
}

/** Gate that requires the admin role. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, isLoading, isAdmin } = useSession();
  if (isLoading) return <PageLoading label="Checking your session…" />;
  if (!user) return <SignInPrompt message="Sign in with an admin account to open this area." />;
  if (!isAdmin) {
    return <ForbiddenState message="This area is only available to admins." />;
  }
  return <>{children}</>;
}
