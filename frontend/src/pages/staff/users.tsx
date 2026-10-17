import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Award, Search, ShieldCheck, UserCog } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { toast } from "sonner";

import { grantBadge, updateUserRole, updateUserStatus } from "@/api/admin";
import type { AdminUserSummary, UserRole } from "@/api/types";
import { RoleBadge } from "@/components/domain/indicators";
import { UserCell } from "@/components/domain/user-cell";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import { Field } from "@/components/ui/field";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useSession } from "@/hooks/use-auth";
import { useUrlSearchInput } from "@/hooks/use-url-search";
import { useAdminUsers, useBadges } from "@/hooks/queries";
import { formatDate } from "@/lib/utils";

function GrantBadgeDialog({ user, onClose }: { user: AdminUserSummary; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [badgeSlug, setBadgeSlug] = useState("");
  const [reason, setReason] = useState("");
  const badgesQuery = useBadges();

  const mutation = useMutation({
    mutationFn: () => grantBadge(user.id, badgeSlug, { reason: reason.trim() || null }),
    onSuccess: (response) => {
      void queryClient.invalidateQueries({ queryKey: ["staff"] });
      void queryClient.invalidateQueries({ queryKey: ["badges", "user", user.github_username] });
      toast.success(response.message);
      onClose();
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Could not grant the badge."),
  });

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>Grant badge</DialogTitle>
          <DialogDescription>
            Award a badge manually to @{user.github_username}. The action is recorded in the audit
            trail.
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <Field label="Badge" htmlFor="grant-badge" required>
            <Select
              id="grant-badge"
              value={badgeSlug}
              onChange={(event) => setBadgeSlug(event.target.value)}
            >
              <option value="">Select a badge…</option>
              {(badgesQuery.data ?? []).map((badge) => (
                <option key={badge.id} value={badge.slug}>
                  {badge.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Reason" htmlFor="grant-reason" hint="Optional, stored in the audit trail.">
            <Textarea
              id="grant-reason"
              rows={2}
              value={reason}
              onChange={(event) => setReason(event.target.value.slice(0, 300))}
              placeholder="e.g. Winner — kickoff hackathon"
            />
          </Field>
        </DialogBody>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={mutation.isPending}
            disabled={!badgeSlug}
            onClick={() => mutation.mutate()}
          >
            <Award aria-hidden />
            Grant badge
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function StaffUsersPage() {
  const { user: me, isAdmin } = useSession();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);
  const role = params.get("role") ?? "";
  const activeFilter = params.get("active") ?? "";
  const search = params.get("q") ?? "";

  const [searchInput, setSearchInput] = useUrlSearchInput("q");

  const usersQuery = useAdminUsers({
    page,
    page_size: 15,
    search: search || undefined,
    role: role || undefined,
    is_active: activeFilter === "" ? undefined : activeFilter === "true",
  });

  const [grantTarget, setGrantTarget] = useState<AdminUserSummary | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<AdminUserSummary | null>(null);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["staff"] });
    void queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
  };

  const roleMutation = useMutation({
    mutationFn: ({ userId, nextRole }: { userId: string; nextRole: UserRole }) =>
      updateUserRole(userId, { role: nextRole }),
    onSuccess: (updated) => {
      invalidate();
      toast.success(`@${updated.github_username} is now ${updated.role}.`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Role change failed."),
  });

  const statusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      updateUserStatus(userId, { is_active: isActive }),
    onSuccess: (updated) => {
      invalidate();
      toast.success(
        updated.is_active
          ? `@${updated.github_username} reactivated.`
          : `@${updated.github_username} deactivated.`,
      );
      setDeactivateTarget(null);
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Status change failed."),
  });

  const data = usersQuery.data;
  const isSelf = useMemo(() => (user: AdminUserSummary) => me?.id === user.id, [me?.id]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative max-w-xs flex-1">
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-faint"
            aria-hidden
          />
          <Input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search by name or username…"
            className="pl-9.5"
            aria-label="Search users"
          />
        </div>
        <Select
          value={role}
          onChange={(event) =>
            setParams(
              (previous) => {
                const next = new URLSearchParams(previous);
                if (event.target.value) next.set("role", event.target.value);
                else next.delete("role");
                next.delete("page");
                return next;
              },
              { replace: true },
            )
          }
          aria-label="Filter by role"
          className="sm:w-40"
        >
          <option value="">All roles</option>
          <option value="student">Students</option>
          <option value="moderator">Moderators</option>
          <option value="admin">Admins</option>
        </Select>
        <Select
          value={activeFilter}
          onChange={(event) =>
            setParams(
              (previous) => {
                const next = new URLSearchParams(previous);
                if (event.target.value) next.set("active", event.target.value);
                else next.delete("active");
                next.delete("page");
                return next;
              },
              { replace: true },
            )
          }
          aria-label="Filter by status"
          className="sm:w-40"
        >
          <option value="">Any status</option>
          <option value="true">Active</option>
          <option value="false">Deactivated</option>
        </Select>
      </div>

      {usersQuery.isError ? (
        <ErrorState error={usersQuery.error} onRetry={() => usersQuery.refetch()} />
      ) : usersQuery.isPending ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full rounded-xl" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <Card>
            <ul className="divide-y divide-line">
              {data.items.map((user) => (
                <li
                  key={user.id}
                  className="flex flex-col gap-3 px-5 py-4 lg:flex-row lg:items-center lg:justify-between"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <UserCell user={user} className="min-w-0" />
                    {isSelf(user) ? <Badge tone="outline">You</Badge> : null}
                    {!user.is_active ? <Badge tone="danger">Deactivated</Badge> : null}
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
                    <span className="text-xs text-faint">Joined {formatDate(user.created_at)}</span>

                    {isAdmin ? (
                      <Select
                        value={user.role}
                        onChange={(event) =>
                          roleMutation.mutate({
                            userId: user.id,
                            nextRole: event.target.value as UserRole,
                          })
                        }
                        aria-label={`Role for @${user.github_username}`}
                        className="w-36"
                        disabled={isSelf(user)}
                      >
                        <option value="student">Student</option>
                        <option value="moderator">Moderator</option>
                        <option value="admin">Admin</option>
                      </Select>
                    ) : (
                      <RoleBadge role={user.role} />
                    )}

                    {isAdmin ? (
                      <Switch
                        checked={user.is_active}
                        disabled={isSelf(user)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            statusMutation.mutate({ userId: user.id, isActive: true });
                          } else {
                            setDeactivateTarget(user);
                          }
                        }}
                        aria-label={`Account status for @${user.github_username}`}
                      />
                    ) : null}

                    <Button variant="secondary" size="sm" onClick={() => setGrantTarget(user)}>
                      <Award aria-hidden />
                      Badge
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
          <Pagination
            page={data.page}
            pages={data.pages}
            onPageChange={(next) =>
              setParams((previous) => {
                const nextParams = new URLSearchParams(previous);
                nextParams.set("page", String(next));
                return nextParams;
              })
            }
          />
        </>
      ) : (
        <EmptyState
          icon={<UserCog className="size-5" aria-hidden />}
          title="No users match"
          description="Adjust the search or filters."
        />
      )}

      {grantTarget ? (
        <GrantBadgeDialog user={grantTarget} onClose={() => setGrantTarget(null)} />
      ) : null}

      <AlertDialog
        open={Boolean(deactivateTarget)}
        onOpenChange={(open) => !open && setDeactivateTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogTitle>Deactivate @{deactivateTarget?.github_username}?</AlertDialogTitle>
          <AlertDialogDescription>
            The account keeps its data but can no longer sign in or submit. This can be undone at
            any time.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                deactivateTarget &&
                statusMutation.mutate({ userId: deactivateTarget.id, isActive: false })
              }
            >
              <ShieldCheck aria-hidden />
              Deactivate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
