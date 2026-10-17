import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Award, Info, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { createBadge, updateBadge } from "@/api/admin";
import type { Badge, BadgeRule, BadgeRuleType } from "@/api/types";
import { BadgeIcon } from "@/components/domain/indicators";
import { Alert, EmptyState, ErrorState } from "@/components/ui/feedback";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Field } from "@/components/ui/field";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useBadges } from "@/hooks/queries";
import { useSession } from "@/hooks/use-auth";
import { qk } from "@/lib/query-keys";

/* ---------------------------------------------------------------------------
 * Rule definitions — mirrors backend/app/models/enums.py::BadgeRuleType and
 * the BadgeRule schema bounds (count 1–100, track 2–64 chars).
 * ------------------------------------------------------------------------ */

const ICON_OPTIONS = ["rocket", "medal", "flame", "trophy", "star"] as const;

const RULE_OPTIONS: {
  value: BadgeRuleType;
  label: string;
  unit: { one: string; many: string };
  needsTrack: boolean;
}[] = [
  {
    value: "submissions_finalized",
    label: "Finalized submissions",
    unit: { one: "finalized submission", many: "finalized submissions" },
    needsTrack: false,
  },
  {
    value: "challenges_passed",
    label: "Challenges passed",
    unit: { one: "challenge passed", many: "challenges passed" },
    needsTrack: false,
  },
  {
    value: "perfect_scores",
    label: "Perfect scores",
    unit: { one: "perfect score", many: "perfect scores" },
    needsTrack: false,
  },
  {
    value: "track_challenges_passed",
    label: "Track challenges passed",
    unit: { one: "challenge passed in a track", many: "challenges passed in a track" },
    needsTrack: true,
  },
];

function ruleSummary(rule: BadgeRule): string {
  const option = RULE_OPTIONS.find((item) => item.value === rule.type);
  const label = option ? (rule.count === 1 ? option.unit.one : option.unit.many) : rule.type;
  return `${rule.count} ${label}${rule.track ? ` · ${rule.track}` : ""}`;
}

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

interface BadgeFormState {
  slug: string;
  name: string;
  description: string;
  icon: string;
  criteriaDescription: string;
  ruleType: BadgeRuleType;
  count: string;
  track: string;
  isActive: boolean;
}

function emptyForm(): BadgeFormState {
  return {
    slug: "",
    name: "",
    description: "",
    icon: "rocket",
    criteriaDescription: "",
    ruleType: "challenges_passed",
    count: "1",
    track: "",
    isActive: true,
  };
}

function formFromBadge(badge: Badge): BadgeFormState {
  return {
    slug: badge.slug,
    name: badge.name,
    description: badge.description,
    icon: badge.icon,
    criteriaDescription: badge.criteria?.description ?? "",
    ruleType: badge.criteria?.rule.type ?? "challenges_passed",
    count: String(badge.criteria?.rule.count ?? 1),
    track: badge.criteria?.rule.track ?? "",
    isActive: true,
  };
}

function BadgeFormDialog({ badge, onClose }: { badge: Badge | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const isEdit = Boolean(badge);
  // Mounted only while open (see StaffBadgesPage), so initial state is fresh.
  const [form, setForm] = useState<BadgeFormState>(() =>
    badge ? formFromBadge(badge) : emptyForm(),
  );
  const [submitted, setSubmitted] = useState(false);

  const patch = (partial: Partial<BadgeFormState>) =>
    setForm((previous) => ({ ...previous, ...partial }));

  const ruleOption = RULE_OPTIONS.find((item) => item.value === form.ruleType);
  const countNumber = Number(form.count);

  const errors: Record<string, string> = {};
  if (!isEdit) {
    if (!form.slug.trim() || !SLUG_PATTERN.test(form.slug.trim()))
      errors.slug = "Lowercase letters, numbers and single dashes (3–64 characters).";
  }
  if (form.name.trim().length < 3 || form.name.trim().length > 120)
    errors.name = "Between 3 and 120 characters.";
  if (form.description.trim().length < 3 || form.description.trim().length > 1000)
    errors.description = "Between 3 and 1000 characters.";
  if (form.criteriaDescription.trim().length < 3 || form.criteriaDescription.trim().length > 300)
    errors.criteriaDescription = "Between 3 and 300 characters.";
  if (!Number.isInteger(countNumber) || countNumber < 1 || countNumber > 100)
    errors.count = "Between 1 and 100.";
  if (ruleOption?.needsTrack && (form.track.trim().length < 2 || form.track.trim().length > 64))
    errors.track = "Between 2 and 64 characters.";

  const hasErrors = Object.keys(errors).length > 0;

  const mutation = useMutation({
    mutationFn: async (): Promise<Badge> => {
      const criteria = {
        description: form.criteriaDescription.trim(),
        rule: {
          type: form.ruleType,
          count: countNumber,
          track: ruleOption?.needsTrack ? form.track.trim() : null,
        },
      };
      if (isEdit && badge) {
        return updateBadge(badge.id, {
          name: form.name.trim(),
          description: form.description.trim(),
          icon: form.icon,
          criteria,
          is_active: form.isActive,
        });
      }
      return createBadge({
        slug: form.slug.trim(),
        name: form.name.trim(),
        description: form.description.trim(),
        icon: form.icon,
        criteria,
        is_active: form.isActive,
      });
    },
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey: qk.badges.all });
      toast.success(isEdit ? `"${saved.name}" updated.` : `"${saved.name}" created.`);
      onClose();
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Could not save the badge."),
  });

  function handleSubmit() {
    setSubmitted(true);
    if (hasErrors || mutation.isPending) return;
    mutation.mutate();
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit badge" : "New badge"}</DialogTitle>
          <DialogDescription>
            Badges award automatically when the rule matches — or manually from the staff users
            page.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="space-y-4">
          <div className="flex items-start gap-4 rounded-xl border border-line bg-surface-2/50 p-4">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
              <BadgeIcon icon={form.icon} className="size-5.5" />
            </span>
            <div>
              <p className="text-sm font-medium text-ink">{form.name.trim() || "Badge preview"}</p>
              <p className="mt-0.5 text-xs text-muted">
                {form.criteriaDescription.trim() || "Criteria description appears here."}
              </p>
              <p className="mt-1 font-mono text-[11px] text-faint">
                {ruleOption?.needsTrack
                  ? ruleSummary({
                      type: form.ruleType,
                      count: Number.isFinite(countNumber) ? countNumber : 1,
                      track: form.track.trim() || null,
                    })
                  : ruleSummary({
                      type: form.ruleType,
                      count: Number.isFinite(countNumber) ? countNumber : 1,
                      track: null,
                    })}
              </p>
            </div>
          </div>

          {!isEdit ? (
            <Field
              label="Slug"
              htmlFor="badge-slug"
              required
              hint="Fixed after creation, e.g. first-steps"
              error={submitted ? errors.slug : null}
            >
              <Input
                id="badge-slug"
                value={form.slug}
                onChange={(event) => patch({ slug: event.target.value.toLowerCase() })}
                placeholder="first-steps"
                spellCheck={false}
                className="font-mono"
                invalid={submitted && Boolean(errors.slug)}
              />
            </Field>
          ) : null}

          <Field label="Name" htmlFor="badge-name" required error={submitted ? errors.name : null}>
            <Input
              id="badge-name"
              value={form.name}
              onChange={(event) => patch({ name: event.target.value })}
              placeholder="First steps"
              invalid={submitted && Boolean(errors.name)}
            />
          </Field>

          <Field
            label="Description"
            htmlFor="badge-description"
            required
            error={submitted ? errors.description : null}
          >
            <Textarea
              id="badge-description"
              rows={2}
              value={form.description}
              onChange={(event) => patch({ description: event.target.value })}
              invalid={submitted && Boolean(errors.description)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Icon">
              <Select value={form.icon} onChange={(event) => patch({ icon: event.target.value })}>
                {ICON_OPTIONS.map((icon) => (
                  <option key={icon} value={icon}>
                    {icon}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Rule">
              <Select
                value={form.ruleType}
                onChange={(event) =>
                  patch({
                    ruleType: event.target.value as BadgeRuleType,
                    track: "",
                  })
                }
              >
                {RULE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field
            label="Criteria description"
            htmlFor="badge-criteria"
            required
            hint="Student-facing explanation of how to earn it."
            error={submitted ? errors.criteriaDescription : null}
          >
            <Input
              id="badge-criteria"
              value={form.criteriaDescription}
              onChange={(event) => patch({ criteriaDescription: event.target.value })}
              placeholder="Pass 3 challenges"
              invalid={submitted && Boolean(errors.criteriaDescription)}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Count"
              htmlFor="badge-count"
              required
              error={submitted ? errors.count : null}
            >
              <Input
                id="badge-count"
                type="number"
                min={1}
                max={100}
                value={form.count}
                onChange={(event) => patch({ count: event.target.value })}
                invalid={submitted && Boolean(errors.count)}
              />
            </Field>
            {ruleOption?.needsTrack ? (
              <Field
                label="Track"
                htmlFor="badge-track"
                required
                error={submitted ? errors.track : null}
              >
                <Input
                  id="badge-track"
                  value={form.track}
                  onChange={(event) => patch({ track: event.target.value.toLowerCase() })}
                  placeholder="web"
                  spellCheck={false}
                  invalid={submitted && Boolean(errors.track)}
                />
              </Field>
            ) : null}
          </div>

          <div className="flex items-center justify-between rounded-xl border border-line px-4 py-3">
            <div>
              <p className="text-sm font-medium text-ink">Active</p>
              <p className="text-xs text-muted">
                Inactive badges stay awarded but are not granted again.
              </p>
            </div>
            <Switch
              checked={form.isActive}
              onCheckedChange={(checked) => patch({ isActive: checked })}
              aria-label="Badge active"
            />
          </div>
        </DialogBody>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={mutation.isPending} onClick={handleSubmit}>
            {isEdit ? "Save changes" : "Create badge"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function StaffBadgesPage() {
  const { isAdmin } = useSession();
  const badgesQuery = useBadges();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBadge, setEditingBadge] = useState<Badge | null>(null);

  function openCreate() {
    setEditingBadge(null);
    setDialogOpen(true);
  }

  function openEdit(badge: Badge) {
    setEditingBadge(badge);
    setDialogOpen(true);
  }

  const badges = badgesQuery.data ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-ink">Badge catalogue</h2>
          <p className="mt-0.5 text-sm text-muted">
            {badges.length} badge{badges.length === 1 ? "" : "s"} · rules are evaluated every time a
            submission is finalized.
          </p>
        </div>
        {isAdmin ? (
          <Button onClick={openCreate}>
            <Plus aria-hidden />
            New badge
          </Button>
        ) : null}
      </div>

      {!isAdmin ? (
        <Alert tone="info">
          Moderators can review the catalogue. Creating and editing badges requires an admin role.
        </Alert>
      ) : null}

      {badgesQuery.isError ? (
        <ErrorState error={badgesQuery.error} onRetry={() => badgesQuery.refetch()} />
      ) : badgesQuery.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32 rounded-xl" />
          ))}
        </div>
      ) : badges.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {badges.map((badge) => (
            <Card key={badge.id}>
              <CardContent className="flex gap-4 p-5">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                  <BadgeIcon icon={badge.icon} className="size-5.5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-ink">{badge.name}</h3>
                      <p className="font-mono text-[11px] text-faint">{badge.slug}</p>
                    </div>
                    {isAdmin ? (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={`Edit ${badge.name}`}
                        onClick={() => openEdit(badge)}
                      >
                        <Pencil aria-hidden />
                      </Button>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-sm text-muted">{badge.description}</p>
                  <p className="mt-2 flex items-center gap-1.5 text-xs text-faint">
                    <Info className="size-3.5 shrink-0" aria-hidden />
                    {ruleSummary(badge.criteria.rule)}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Award className="size-5" aria-hidden />}
          title="No badges yet"
          description={
            isAdmin
              ? "Create the first badge to reward student progress."
              : "An admin has not created any badges yet."
          }
          action={
            isAdmin ? (
              <Button onClick={openCreate}>
                <Plus aria-hidden />
                New badge
              </Button>
            ) : undefined
          }
        />
      )}

      {dialogOpen ? (
        <BadgeFormDialog
          badge={editingBadge}
          onClose={() => {
            setDialogOpen(false);
            setEditingBadge(null);
          }}
        />
      ) : null}
    </div>
  );
}
