import { NavLink, Outlet } from "react-router";

import { RequireStaff } from "@/components/common/guards";
import { RoleBadge } from "@/components/domain/indicators";
import { PageContainer } from "@/components/layout/page-container";
import { usePageTitle } from "@/hooks/use-page-title";
import { useSession } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const TABS = [
  { to: "/staff", label: "Overview", end: true, adminOnly: false },
  { to: "/staff/challenges", label: "Challenges", end: false, adminOnly: false },
  { to: "/staff/submissions", label: "Moderation", end: false, adminOnly: false },
  { to: "/staff/users", label: "Users", end: false, adminOnly: false },
  { to: "/staff/badges", label: "Badges", end: false, adminOnly: false },
  { to: "/staff/audit", label: "Audit log", end: false, adminOnly: true },
];

export function StaffLayout() {
  usePageTitle("Staff console");
  const { user, isAdmin } = useSession();
  const visibleTabs = TABS.filter((tab) => !tab.adminOnly || isAdmin);

  return (
    <RequireStaff>
      <PageContainer className="py-8 sm:py-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-[1.7rem]">
              Staff console
            </h1>
            <p className="mt-1 text-sm text-muted">
              Challenge authoring, moderation and platform administration.
            </p>
          </div>
          {user ? <RoleBadge role={user.role} /> : null}
        </div>

        <nav
          className="mt-5 flex gap-1 overflow-x-auto border-b border-line pb-px"
          aria-label="Staff sections"
        >
          {visibleTabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                cn(
                  "-mb-px rounded-t-lg border-b-2 px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
                  isActive
                    ? "border-primary text-ink"
                    : "border-transparent text-muted hover:border-line-strong hover:text-ink",
                )
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-6">
          <Outlet />
        </div>
      </PageContainer>
    </RequireStaff>
  );
}
