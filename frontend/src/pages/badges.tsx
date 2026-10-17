import { useMemo } from "react";
import { Link } from "react-router";

import { BadgeTile } from "@/components/domain/badge-tile";
import { buttonClasses } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer, PageHeader } from "@/components/layout/page-container";
import { useSession } from "@/hooks/use-auth";
import { usePageTitle } from "@/hooks/use-page-title";
import { useBadges, useUserBadges } from "@/hooks/queries";

export function BadgesPage() {
  usePageTitle("Badges");
  const { user, isStaff } = useSession();
  const badgesQuery = useBadges();
  const myBadgesQuery = useUserBadges(user?.github_username);

  const awardedBySlug = useMemo(() => {
    const map = new Map<string, string>();
    for (const entry of myBadgesQuery.data ?? []) map.set(entry.badge.slug, entry.awarded_at);
    return map;
  }, [myBadgesQuery.data]);

  const badges = badgesQuery.data ?? [];

  return (
    <PageContainer className="py-8 sm:py-10">
      <PageHeader
        title="Badges"
        description="Earned automatically as your work gets finalized and scored — no applications needed."
        actions={
          isStaff ? (
            <Link to="/staff/badges" className={buttonClasses({ variant: "secondary" })}>
              Manage badges
            </Link>
          ) : null
        }
      />

      <div className="mt-6">
        {badgesQuery.isError ? (
          <ErrorState error={badgesQuery.error} onRetry={() => badgesQuery.refetch()} />
        ) : badgesQuery.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-28 w-full rounded-xl" />
            ))}
          </div>
        ) : badges.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {badges.map((badge) => (
              <BadgeTile
                key={badge.id}
                badge={badge}
                awardedAt={awardedBySlug.get(badge.slug) ?? null}
                locked={Boolean(user) && !awardedBySlug.has(badge.slug)}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No badges configured"
            description="Badges will appear here once organizers add them."
          />
        )}
      </div>
    </PageContainer>
  );
}
