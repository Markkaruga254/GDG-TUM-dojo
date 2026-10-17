import { ArrowRight, ClipboardList, ListChecks, Plus, ScrollText, Users } from "lucide-react";
import { Link } from "react-router";

import { StatCard } from "@/components/domain/stat-card";
import { buttonClasses } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useSession } from "@/hooks/use-auth";
import { useAdminUsers, useChallenges } from "@/hooks/queries";
import { formatNumber } from "@/lib/utils";

export function StaffOverviewPage() {
  const { isAdmin } = useSession();
  const challengesQuery = useChallenges({ page_size: 1 });
  const usersQuery = useAdminUsers({ page_size: 1 });

  const links = [
    {
      to: "/staff/challenges",
      icon: ListChecks,
      title: "Manage challenges",
      body: "Draft, configure evaluations, publish and archive challenges.",
    },
    {
      to: "/staff/submissions",
      icon: ClipboardList,
      title: "Moderate submissions",
      body: "Review submissions per challenge, disqualify or reinstate, adjust scores.",
    },
    {
      to: "/staff/users",
      icon: Users,
      title: "Users & roles",
      body: "Search builders, manage roles and account status, grant badges.",
    },
    ...(isAdmin
      ? [
          {
            to: "/staff/audit",
            icon: ScrollText,
            title: "Audit log",
            body: "Every staff mutation is recorded — inspect the trail here.",
          },
        ]
      : []),
  ];

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Challenges (all statuses)"
          value={challengesQuery.data ? formatNumber(challengesQuery.data.total) : "—"}
        />
        <StatCard
          label="Registered users"
          value={usersQuery.data ? formatNumber(usersQuery.data.total) : "—"}
        />
        <StatCard
          label="Your role"
          value={isAdmin ? "Admin" : "Moderator"}
          hint={isAdmin ? "Full platform control" : "Moderation & authoring"}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="group flex items-start gap-4 rounded-xl border border-line bg-surface p-5 shadow-card transition-[border-color,transform] hover:-translate-y-0.5 hover:border-line-strong"
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
              <link.icon className="size-5" aria-hidden />
            </span>
            <span className="min-w-0">
              <span className="flex items-center gap-1.5 text-sm font-semibold text-ink group-hover:text-primary">
                {link.title}
                <ArrowRight
                  className="size-3.5 transition-transform group-hover:translate-x-0.5"
                  aria-hidden
                />
              </span>
              <span className="mt-1 block text-sm text-muted">{link.body}</span>
            </span>
          </Link>
        ))}
      </div>

      <Card>
        <CardContent className="flex flex-col items-start justify-between gap-4 p-5 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-semibold text-ink">Author a new challenge</p>
            <p className="mt-0.5 text-sm text-muted">
              Define the brief, scoring checks and the submission window — then publish when ready.
            </p>
          </div>
          <Link to="/staff/challenges/new" className={buttonClasses({ className: "shrink-0" })}>
            <Plus aria-hidden />
            New challenge
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
