import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Menu, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink } from "react-router";

import { GitHubIcon } from "@/components/common/github-icon";
import { Logo } from "@/components/common/logo";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { UserMenu } from "@/components/common/user-menu";
import { Button, buttonClasses } from "@/components/ui/button";
import { githubLoginUrl } from "@/api/auth";
import { useSession } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { to: "/challenges", label: "Challenges" },
  { to: "/leaderboard", label: "Leaderboard" },
  { to: "/badges", label: "Badges" },
];

function navLinkClasses({ isActive }: { isActive: boolean }): string {
  return cn(
    "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
    isActive ? "bg-surface-2 text-ink" : "text-muted hover:bg-surface-2/60 hover:text-ink",
  );
}

function MobileNav({ isStaff }: { isStaff: boolean }) {
  const [open, setOpen] = useState(false);

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Trigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
          <Menu aria-hidden />
        </Button>
      </DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/55 backdrop-blur-[2px] data-[state=open]:animate-fade-in md:hidden" />
        <DialogPrimitive.Content
          aria-label="Navigation menu"
          aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-50 flex w-72 max-w-[85vw] flex-col border-l border-line bg-surface p-5 shadow-pop focus:outline-none data-[state=open]:animate-slide-in md:hidden"
        >
          <div className="flex items-center justify-between">
            <Logo />
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close menu">
                <X aria-hidden />
              </Button>
            </DialogPrimitive.Close>
          </div>
          <nav className="mt-6 flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-surface-2 text-ink"
                      : "text-muted hover:bg-surface-2 hover:text-ink",
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
            {isStaff ? (
              <NavLink
                to="/staff"
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-surface-2 text-ink"
                      : "text-muted hover:bg-surface-2 hover:text-ink",
                  )
                }
              >
                Staff console
              </NavLink>
            ) : null}
          </nav>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export function Navbar() {
  const { user, isAuthenticated, isStaff } = useSession();

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-15 w-full max-w-6xl items-center gap-2 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="mr-2 shrink-0 rounded-lg" aria-label="Build Arena home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
          {NAV_LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} className={navLinkClasses}>
              {link.label}
            </NavLink>
          ))}
          {isStaff ? (
            <NavLink to="/staff" className={navLinkClasses}>
              Staff
            </NavLink>
          ) : null}
        </nav>
        <div className="ml-auto flex items-center gap-1.5">
          <ThemeToggle />
          {isAuthenticated && user ? (
            <UserMenu user={user} isStaff={isStaff} />
          ) : (
            <a
              href={githubLoginUrl()}
              className={buttonClasses({ size: "md", className: "ml-1 max-sm:hidden" })}
            >
              <GitHubIcon aria-hidden />
              Sign in
            </a>
          )}
          <MobileNav isStaff={isStaff} />
        </div>
      </div>
    </header>
  );
}
