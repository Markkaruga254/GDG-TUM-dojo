import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { logout } from "@/api/auth";
import type { UserSelf } from "@/api/types";
import { updateMe } from "@/api/users";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { RoleBadge } from "@/components/domain/indicators";
import { useSession } from "@/hooks/use-auth";
import { usePageTitle } from "@/hooks/use-page-title";
import { PageContainer, PageHeader } from "@/components/layout/page-container";
import { qk } from "@/lib/query-keys";
import { formatDate } from "@/lib/utils";

function SettingsSkeleton() {
  return (
    <PageContainer className="max-w-3xl py-8 sm:py-10">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="mt-2 h-4 w-72" />
      <Skeleton className="mt-6 h-72 w-full rounded-xl" />
      <Skeleton className="mt-6 h-24 w-full rounded-xl" />
    </PageContainer>
  );
}

export function SettingsPage() {
  usePageTitle("Settings");
  const { user, isLoading } = useSession();

  if (isLoading) return <SettingsSkeleton />;
  // Signed-out visitors are handled by the RequireAuth wrapper.
  if (!user) return null;

  return <SettingsContent user={user} />;
}

function SettingsContent({ user }: { user: UserSelf }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // The form owns its working copy; `user` is the last-saved snapshot, so the
  // reset button and dirty check can compare against it without an effect.
  const [displayName, setDisplayName] = useState(user.display_name ?? "");
  const [bio, setBio] = useState(user.bio ?? "");

  const saveMutation = useMutation({
    mutationFn: () =>
      updateMe({
        display_name: displayName.trim() ? displayName.trim() : null,
        bio: bio.trim() ? bio.trim() : null,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(qk.me, updated);
      if (updated.github_username) {
        void queryClient.invalidateQueries({
          queryKey: qk.profiles.profile(updated.github_username),
        });
      }
      toast.success("Profile updated.");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Update failed."),
  });

  const signOut = useMutation({
    mutationFn: logout,
    onSettled: () => {
      queryClient.setQueryData(qk.me, null);
      queryClient.clear();
      toast.success("Signed out.");
      navigate("/");
    },
  });

  const dirty = (user.display_name ?? "") !== displayName.trim() || (user.bio ?? "") !== bio.trim();

  return (
    <PageContainer className="max-w-3xl py-8 sm:py-10">
      <PageHeader title="Settings" description="Your public profile and session." />

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <RoleBadge role={user.role} />
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center gap-4 rounded-lg border border-line bg-surface-2/50 p-4">
            <Avatar user={user} size="lg" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink">@{user.github_username}</p>
              <p className="text-xs text-faint">
                GitHub account · joined {formatDate(user.created_at)}
              </p>
            </div>
            <Badge tone="outline" className="ml-auto">
              Synced with GitHub
            </Badge>
          </div>

          <Field
            label="Display name"
            htmlFor="display-name"
            hint="Shown on the leaderboard and your profile. Leave empty to use your GitHub username."
          >
            <Input
              id="display-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value.slice(0, 120))}
              placeholder={user.github_username}
            />
          </Field>

          <Field
            label="Bio"
            htmlFor="bio"
            hint={`${bio.length}/500 characters — a short line about what you build.`}
          >
            <Textarea
              id="bio"
              value={bio}
              onChange={(event) => setBio(event.target.value.slice(0, 500))}
              placeholder="Full-stack builder · loves edge cases"
              rows={3}
            />
          </Field>

          <div className="flex items-center justify-end gap-2">
            <Button
              variant="ghost"
              disabled={!dirty || saveMutation.isPending}
              onClick={() => {
                setDisplayName(user.display_name ?? "");
                setBio(user.bio ?? "");
              }}
            >
              Reset
            </Button>
            <Button
              loading={saveMutation.isPending}
              disabled={!dirty}
              onClick={() => saveMutation.mutate()}
            >
              Save changes
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Session</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted">
            Signing out revokes the current session token on the server.
          </p>
          <Button
            variant="secondary"
            loading={signOut.isPending}
            onClick={() => signOut.mutate()}
            className="shrink-0 text-danger [&_svg]:text-danger"
          >
            <LogOut aria-hidden />
            Sign out
          </Button>
        </CardContent>
      </Card>
    </PageContainer>
  );
}
