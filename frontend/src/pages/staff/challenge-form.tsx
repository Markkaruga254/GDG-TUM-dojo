import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, ListPlus, Plus, Rocket, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "sonner";

import { createChallenge, publishChallenge, updateChallenge } from "@/api/challenges";
import type { ChallengeCreatePayload, ChallengeUpdatePayload, EvaluationCheck } from "@/api/types";
import { ChallengeStatusBadge } from "@/components/domain/indicators";
import { Alert, EmptyState } from "@/components/ui/feedback";
import { Button, buttonClasses } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox, Switch } from "@/components/ui/checkbox";
import { Field } from "@/components/ui/field";
import { Input, Select, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useChallenge, useChallenges } from "@/hooks/queries";
import { usePageTitle } from "@/hooks/use-page-title";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

/* ---------------------------------------------------------------------------
 * Evaluation check definitions — mirrors backend/app/evaluation/rules.py
 * ------------------------------------------------------------------------ */

const CHECK_TYPES = [
  "repo_accessible",
  "repo_public",
  "required_files",
  "required_directories",
  "readme_present",
  "readme_sections",
  "readme_min_length",
  "evidence_links",
  "min_commits",
  "license_present",
  "language_present",
] as const;

type CheckType = (typeof CHECK_TYPES)[number];

const CHECK_TYPE_DESCRIPTIONS: Record<CheckType, string> = {
  repo_accessible: "Repository exists and is reachable through the GitHub API.",
  repo_public: "Repository is publicly visible.",
  required_files: "Required files exist in the repository.",
  required_directories: "Required directories exist in the repository.",
  readme_present: "Repository has a README.",
  readme_sections: "README documents the required sections.",
  readme_min_length: "README has a minimum length.",
  evidence_links: "Submission includes the required evidence links.",
  min_commits: "Repository has a minimum number of commits.",
  license_present: "Repository declares a license.",
  language_present: "Repository uses the required language(s).",
};

const CHECK_ID_PATTERN = /^[a-z0-9][a-z0-9_-]{2,63}$/;
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const TRACK_PATTERN = /^[a-z0-9][a-z0-9 _+-]{1,63}$/;

const defaultParamsFor = (type: CheckType): Record<string, unknown> => {
  switch (type) {
    case "required_files":
    case "required_directories":
      return { paths: [], match: "all" };
    case "readme_sections":
      return { sections: [] };
    case "readme_min_length":
      return { min_characters: 300 };
    case "evidence_links":
      return { min_count: 1 };
    case "min_commits":
      return { min_count: 1 };
    case "language_present":
      return { languages: [], min_share: 0 };
    default:
      return {};
  }
};

interface FormCheck {
  key: number;
  id: string;
  type: CheckType;
  description: string;
  points: number;
  required: boolean;
  enabled: boolean;
  params: Record<string, unknown>;
}

let checkKeySeed = 0;

function makeCheck(partial: Partial<FormCheck> = {}): FormCheck {
  checkKeySeed += 1;
  const type = partial.type ?? "repo_accessible";
  return {
    key: checkKeySeed,
    id: partial.id ?? `check-${checkKeySeed}`,
    type,
    description: partial.description ?? CHECK_TYPE_DESCRIPTIONS[type],
    points: partial.points ?? 10,
    required: partial.required ?? true,
    enabled: partial.enabled ?? true,
    params: partial.params ?? defaultParamsFor(type),
  };
}

function starterChecks(): FormCheck[] {
  return [
    makeCheck({ id: "repo-accessible", type: "repo_accessible", points: 10 }),
    makeCheck({ id: "readme-present", type: "readme_present", points: 10 }),
  ];
}

/* --- check editor ----------------------------------------------------------------- */

function ParamsEditor({
  check,
  onChange,
}: {
  check: FormCheck;
  onChange: (params: Record<string, unknown>) => void;
}) {
  const params = check.params;

  const listToText = (value: unknown): string =>
    Array.isArray(value) ? (value as string[]).join("\n") : "";
  const textToList = (value: string): string[] =>
    value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

  switch (check.type) {
    case "required_files":
    case "required_directories":
      return (
        <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
          <Field
            label={
              check.type === "required_files"
                ? "Paths (one per line)"
                : "Directories (one per line)"
            }
            hint="Repository-relative, e.g. src/main.py or docs"
          >
            <Textarea
              rows={3}
              value={listToText(params.paths)}
              onChange={(event) => onChange({ ...params, paths: textToList(event.target.value) })}
              placeholder={"src\nREADME.md"}
            />
          </Field>
          <Field label="Match">
            <Select
              value={typeof params.match === "string" ? params.match : "all"}
              onChange={(event) => onChange({ ...params, match: event.target.value })}
            >
              <option value="all">All required</option>
              <option value="any">Any present</option>
            </Select>
          </Field>
        </div>
      );
    case "readme_sections":
      return (
        <Field
          label="Sections (one per line)"
          hint="Case-insensitive keyword matches in the README."
        >
          <Textarea
            rows={3}
            value={listToText(params.sections)}
            onChange={(event) => onChange({ ...params, sections: textToList(event.target.value) })}
            placeholder={"installation\nusage"}
          />
        </Field>
      );
    case "readme_min_length":
      return (
        <Field label="Minimum characters">
          <Input
            type="number"
            min={50}
            max={20000}
            value={String(params.min_characters ?? 300)}
            onChange={(event) =>
              onChange({ ...params, min_characters: Number(event.target.value) })
            }
          />
        </Field>
      );
    case "evidence_links":
      return (
        <Field label="Minimum evidence links">
          <Input
            type="number"
            min={1}
            max={20}
            value={String(params.min_count ?? 1)}
            onChange={(event) => onChange({ ...params, min_count: Number(event.target.value) })}
          />
        </Field>
      );
    case "min_commits":
      return (
        <Field label="Minimum commits">
          <Input
            type="number"
            min={1}
            max={100}
            value={String(params.min_count ?? 1)}
            onChange={(event) => onChange({ ...params, min_count: Number(event.target.value) })}
          />
        </Field>
      );
    case "language_present":
      return (
        <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
          <Field label="Languages (one per line)" hint="Matched against the repository languages.">
            <Textarea
              rows={3}
              value={listToText(params.languages)}
              onChange={(event) =>
                onChange({ ...params, languages: textToList(event.target.value) })
              }
              placeholder={"TypeScript\nGo"}
            />
          </Field>
          <Field label="Min share" hint="0–1, 0 = any amount">
            <Input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={String(params.min_share ?? 0)}
              onChange={(event) => onChange({ ...params, min_share: Number(event.target.value) })}
            />
          </Field>
        </div>
      );
    default:
      return <p className="text-xs text-faint">This check has no parameters.</p>;
  }
}

function CheckEditorCard({
  check,
  index,
  onChange,
  onRemove,
}: {
  check: FormCheck;
  index: number;
  onChange: (next: FormCheck) => void;
  onRemove: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-line bg-surface-2/50 p-4",
        !check.enabled && "opacity-60",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold tracking-wide text-faint uppercase">
          Check {index + 1}
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`Remove check ${index + 1}`}
          className="text-danger [&_svg]:text-danger"
          onClick={onRemove}
        >
          <Trash2 aria-hidden />
        </Button>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Type">
          <Select
            value={check.type}
            onChange={(event) => {
              const nextType = event.target.value as CheckType;
              onChange({
                ...check,
                type: nextType,
                params: defaultParamsFor(nextType),
                description: CHECK_TYPE_DESCRIPTIONS[nextType],
              });
            }}
          >
            {CHECK_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Check ID" hint="Unique, lowercase, e.g. readme-present">
          <Input
            value={check.id}
            onChange={(event) => onChange({ ...check, id: event.target.value })}
            spellCheck={false}
            className="font-mono"
          />
        </Field>
        <Field label="Description" className="sm:col-span-2">
          <Input
            value={check.description}
            onChange={(event) => onChange({ ...check, description: event.target.value })}
          />
        </Field>
        <Field label="Points">
          <Input
            type="number"
            min={0}
            max={10000}
            value={String(check.points)}
            onChange={(event) => onChange({ ...check, points: Number(event.target.value) })}
          />
        </Field>
        <div className="flex items-end gap-5 pb-2">
          <Checkbox
            id={`required-${check.key}`}
            checked={check.required}
            onChange={(event) => onChange({ ...check, required: event.target.checked })}
            label="Required"
          />
          <Checkbox
            id={`enabled-${check.key}`}
            checked={check.enabled}
            onChange={(event) => onChange({ ...check, enabled: event.target.checked })}
            label="Enabled"
          />
        </div>
        <div className="sm:col-span-2">
          <ParamsEditor check={check} onChange={(params) => onChange({ ...check, params })} />
        </div>
      </div>
    </div>
  );
}

/* --- helpers ------------------------------------------------------------------------- */

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

function fromLocalInput(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

/* --- page ------------------------------------------------------------------------------- */

export function ChallengeFormPage() {
  const { slug: editSlug } = useParams<{ slug: string }>();
  const isEdit = Boolean(editSlug);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const challengeQuery = useChallenge(editSlug);
  const challenge = challengeQuery.data;

  usePageTitle(isEdit ? `Edit — ${challenge?.title ?? "challenge"}` : "New challenge");

  const [title, setTitle] = useState("");
  const [slugInput, setSlugInput] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [track, setTrack] = useState("");
  const [difficulty, setDifficulty] = useState<"beginner" | "intermediate" | "advanced">(
    "beginner",
  );
  const [tagsInput, setTagsInput] = useState("");
  const [maxPoints, setMaxPoints] = useState("100");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [checks, setChecks] = useState<FormCheck[]>(() => (isEdit ? [] : starterChecks()));
  const [replaceConfig, setReplaceConfig] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const initialized = useRef(false);
  useEffect(() => {
    if (!challenge || initialized.current || !isEdit) return;
    initialized.current = true;
    setTitle(challenge.title);
    setDescription(challenge.description);
    setInstructions(challenge.instructions);
    setTrack(challenge.track);
    setDifficulty(challenge.difficulty);
    setTagsInput(challenge.tags.join(", "));
    setMaxPoints(String(challenge.max_points));
    setStartsAt(toLocalInput(challenge.starts_at));
    setEndsAt(toLocalInput(challenge.ends_at));
  }, [challenge, isEdit]);

  const facetsQuery = useChallenges({ page_size: 100 });
  const knownTracks = useMemo(
    () => Array.from(new Set((facetsQuery.data?.items ?? []).map((item) => item.track))),
    [facetsQuery.data],
  );

  const tags = useMemo(
    () =>
      Array.from(
        new Set(
          tagsInput
            .split(",")
            .map((tag) => tag.trim().toLowerCase())
            .filter(Boolean),
        ),
      ).slice(0, 10),
    [tagsInput],
  );

  const enabledChecks = checks.filter((check) => check.enabled);
  const allocatedPoints = enabledChecks.reduce((total, check) => total + (check.points || 0), 0);
  const maxPointsNumber = Number(maxPoints) || 0;

  /* Validation ---------------------------------------------------------------- */

  const errors = useMemo(() => {
    const result: Record<string, string> = {};
    if (title.trim().length < 3) result.title = "At least 3 characters.";
    if (title.trim().length > 200) result.title = "At most 200 characters.";
    if (!isEdit && slugInput.trim()) {
      if (slugInput.trim().length < 3) result.slug = "At least 3 characters.";
      else if (!SLUG_PATTERN.test(slugInput.trim()))
        result.slug = "Lowercase letters, numbers and single dashes only.";
    }
    if (description.trim().length < 10) result.description = "At least 10 characters.";
    if (instructions.length > 50000) result.instructions = "At most 50,000 characters.";
    const trackValue = track.trim();
    if (!trackValue || !TRACK_PATTERN.test(trackValue))
      result.track = "Lowercase letters, numbers, spaces, +, - or _ (2–64 characters).";
    if (tagsInput && tags.length === 0) result.tags = "Tags could not be parsed.";
    if (!Number.isInteger(maxPointsNumber) || maxPointsNumber < 1 || maxPointsNumber > 10000)
      result.maxPoints = "Between 1 and 10,000.";
    if (startsAt && endsAt && new Date(endsAt) <= new Date(startsAt))
      result.endsAt = "Must be after the start.";
    return result;
  }, [
    title,
    slugInput,
    isEdit,
    description,
    instructions,
    track,
    tagsInput,
    tags,
    maxPointsNumber,
    startsAt,
    endsAt,
  ]);

  const usingEditor = !isEdit || replaceConfig;

  const checkProblems = useMemo(() => {
    if (!usingEditor) return [];
    const problems: string[] = [];
    if (checks.length === 0) problems.push("Add at least one check.");
    if (checks.length > 25) problems.push("At most 25 checks are allowed.");
    const ids = new Set<string>();
    for (const check of checks) {
      if (!CHECK_ID_PATTERN.test(check.id)) {
        problems.push(
          `Check ID "${check.id}" must be lowercase (letters, numbers, -, _) and 3–64 chars.`,
        );
        break;
      }
      if (ids.has(check.id)) {
        problems.push(`Duplicate check ID "${check.id}".`);
        break;
      }
      ids.add(check.id);
      if (check.description.trim().length < 3) {
        problems.push(`Check "${check.id}" needs a description (3+ characters).`);
        break;
      }
      if (check.enabled) {
        const paths = (check.params.paths as string[] | undefined) ?? [];
        const sections = (check.params.sections as string[] | undefined) ?? [];
        const languages = (check.params.languages as string[] | undefined) ?? [];
        if (
          (check.type === "required_files" || check.type === "required_directories") &&
          paths.length === 0
        ) {
          problems.push(`Check "${check.id}" needs at least one path.`);
          break;
        }
        if (check.type === "readme_sections" && sections.length === 0) {
          problems.push(`Check "${check.id}" needs at least one section keyword.`);
          break;
        }
        if (check.type === "language_present" && languages.length === 0) {
          problems.push(`Check "${check.id}" needs at least one language.`);
          break;
        }
      }
    }
    if (problems.length === 0) {
      if (enabledChecks.length === 0) problems.push("At least one check must be enabled.");
      else if (allocatedPoints === 0)
        problems.push("Enabled checks allocate zero points; at least one check must score.");
      else if (allocatedPoints > maxPointsNumber)
        problems.push(
          `Enabled checks allocate ${allocatedPoints} points but the challenge maximum is ${maxPointsNumber}.`,
        );
    }
    return problems;
  }, [usingEditor, checks, enabledChecks.length, allocatedPoints, maxPointsNumber]);

  const hasErrors = Object.keys(errors).length > 0 || checkProblems.length > 0;

  /* Mutations ---------------------------------------------------------------------- */

  function buildBasePayload(): Omit<ChallengeCreatePayload, "slug"> {
    return {
      title: title.trim(),
      description: description.trim(),
      instructions: instructions.trim(),
      track: track.trim(),
      difficulty,
      tags,
      max_points: maxPointsNumber,
      starts_at: fromLocalInput(startsAt),
      ends_at: fromLocalInput(endsAt),
      evaluation_config: {
        version: 1,
        require_public_repo: true,
        checks: checks.map<EvaluationCheck>((check) => ({
          id: check.id,
          type: check.type,
          description: check.description.trim(),
          points: check.points,
          required: check.required,
          enabled: check.enabled,
          params: check.params,
        })),
      },
    };
  }

  const saveMutation = useMutation({
    mutationFn: async (): Promise<{ slug: string; title: string }> => {
      if (isEdit && challenge) {
        const payload: ChallengeUpdatePayload = { ...buildBasePayload() };
        if (!replaceConfig) delete payload.evaluation_config;
        const updated = await updateChallenge(challenge.id, payload);
        return { slug: updated.slug, title: updated.title };
      }
      const created = await createChallenge({
        ...buildBasePayload(),
        slug: slugInput.trim() ? slugInput.trim() : undefined,
      });
      return { slug: created.slug, title: created.title };
    },
    onSuccess: ({ slug, title: savedTitle }) => {
      void queryClient.invalidateQueries({ queryKey: qk.challenges.all });
      toast.success(isEdit ? `"${savedTitle}" saved.` : `"${savedTitle}" created as a draft.`);
      navigate(`/staff/challenges/${slug}/edit`);
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : "Could not save the challenge."),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishChallenge(challenge!.id),
    onSuccess: (published) => {
      void queryClient.invalidateQueries({ queryKey: qk.challenges.all });
      toast.success(`"${published.title}" is live.`);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Publish failed."),
  });

  function handleSubmit() {
    setSubmitted(true);
    if (hasErrors || saveMutation.isPending) return;
    saveMutation.mutate();
  }

  if (isEdit && challengeQuery.isPending) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-72 w-full rounded-xl" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (isEdit && (challengeQuery.isError || !challenge)) {
    return (
      <EmptyState
        title="Challenge not found"
        description="It may have been deleted, or the link is stale."
        action={
          <Link to="/staff/challenges" className={buttonClasses({ variant: "secondary" })}>
            Back to challenges
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/staff/challenges"
          className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="size-3.5" aria-hidden />
          All challenges
        </Link>
        <div className="flex items-center gap-2">
          {isEdit && challenge ? <ChallengeStatusBadge status={challenge.status} /> : null}
          {isEdit && challenge && challenge.status !== "published" ? (
            <Button
              size="sm"
              variant="secondary"
              loading={publishMutation.isPending}
              disabled={submitted && hasErrors}
              onClick={() => publishMutation.mutate()}
            >
              <Rocket aria-hidden />
              {challenge.status === "draft" ? "Publish" : "Republish"}
            </Button>
          ) : null}
        </div>
      </div>

      {isEdit && challenge && challenge.status === "draft" ? (
        <Alert tone="info" title="Draft challenges are invisible to students.">
          Fill in the brief, configure the checks and publish when everything is ready. Publishing
          validates the configuration one more time on the server.
        </Alert>
      ) : null}

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Brief</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Title"
            htmlFor="challenge-title"
            required
            error={submitted ? errors.title : null}
            className="sm:col-span-2"
          >
            <Input
              id="challenge-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Ship a real-time dashboard"
              invalid={submitted && Boolean(errors.title)}
            />
          </Field>

          {!isEdit ? (
            <Field
              label="Slug"
              htmlFor="challenge-slug"
              hint="Optional — generated from the title when empty."
              error={submitted ? errors.slug : null}
            >
              <Input
                id="challenge-slug"
                value={slugInput}
                onChange={(event) => setSlugInput(event.target.value)}
                placeholder={slugify(title) || "real-time-dashboard"}
                spellCheck={false}
                className="font-mono"
                invalid={submitted && Boolean(errors.slug)}
              />
            </Field>
          ) : (
            <Field label="Slug" hint="Fixed after creation.">
              <Input value={challenge?.slug ?? ""} readOnly disabled className="font-mono" />
            </Field>
          )}

          <Field
            label="Track"
            htmlFor="challenge-track"
            required
            error={submitted ? errors.track : null}
          >
            <Input
              id="challenge-track"
              value={track}
              onChange={(event) => setTrack(event.target.value.toLowerCase())}
              placeholder="web"
              list="known-tracks"
              spellCheck={false}
              invalid={submitted && Boolean(errors.track)}
            />
            <datalist id="known-tracks">
              {knownTracks.map((value) => (
                <option key={value} value={value} />
              ))}
            </datalist>
          </Field>

          <Field
            label="Description"
            htmlFor="challenge-description"
            required
            error={submitted ? errors.description : null}
            className="sm:col-span-2"
          >
            <Textarea
              id="challenge-description"
              rows={4}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What should students build, and what makes it interesting?"
              invalid={submitted && Boolean(errors.description)}
            />
          </Field>

          <Field
            label="Instructions"
            htmlFor="challenge-instructions"
            hint="Optional — requirements, constraints, submission hints."
            error={submitted ? errors.instructions : null}
            className="sm:col-span-2"
          >
            <Textarea
              id="challenge-instructions"
              rows={5}
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              placeholder={"Must expose /api/health\nUse PostgreSQL for persistence"}
            />
          </Field>

          <Field
            label="Tags"
            htmlFor="challenge-tags"
            hint="Comma separated, up to 10 — used for discovery filters."
          >
            <Input
              id="challenge-tags"
              value={tagsInput}
              onChange={(event) => setTagsInput(event.target.value)}
              placeholder="api, realtime, postgres"
              spellCheck={false}
            />
          </Field>
          {tags.length > 0 ? (
            <div className="flex flex-wrap items-end gap-1.5 pb-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-md bg-surface-2 px-2 py-0.5 font-mono text-[11px] text-muted"
                >
                  #{tag}
                </span>
              ))}
            </div>
          ) : null}

          <Field label="Difficulty">
            <Select
              value={difficulty}
              onChange={(event) =>
                setDifficulty(event.target.value as "beginner" | "intermediate" | "advanced")
              }
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </Select>
          </Field>

          <Field
            label="Max points"
            htmlFor="challenge-points"
            required
            error={submitted ? errors.maxPoints : null}
          >
            <Input
              id="challenge-points"
              type="number"
              min={1}
              max={10000}
              value={maxPoints}
              onChange={(event) => setMaxPoints(event.target.value)}
              invalid={submitted && Boolean(errors.maxPoints)}
            />
          </Field>

          <Field
            label="Starts"
            htmlFor="challenge-starts"
            hint="Optional — empty means immediately."
          >
            <Input
              id="challenge-starts"
              type="datetime-local"
              value={startsAt}
              onChange={(event) => setStartsAt(event.target.value)}
            />
          </Field>
          <Field
            label="Ends"
            htmlFor="challenge-ends"
            hint="Optional — empty means open ended."
            error={submitted ? errors.endsAt : null}
          >
            <Input
              id="challenge-ends"
              type="datetime-local"
              value={endsAt}
              onChange={(event) => setEndsAt(event.target.value)}
              invalid={submitted && Boolean(errors.endsAt)}
            />
          </Field>
        </CardContent>
      </Card>

      {/* Evaluation configuration */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Evaluation checks</CardTitle>
            <p className="mt-0.5 text-sm text-muted">
              {usingEditor
                ? `${enabledChecks.length} enabled · ${allocatedPoints} of ${maxPointsNumber} points allocated`
                : "The current configuration is kept as-is."}
            </p>
          </div>
          {isEdit ? (
            <Switch
              checked={replaceConfig}
              onCheckedChange={(checked) => {
                setReplaceConfig(checked);
                if (checked && checks.length === 0 && challenge) {
                  setChecks(
                    challenge.evaluation.map((check) =>
                      makeCheck({
                        id: check.id,
                        type: check.type as CheckType,
                        description: check.description,
                        points: check.points,
                        required: check.required,
                        enabled: check.enabled,
                      }),
                    ),
                  );
                }
              }}
              label="Replace"
            />
          ) : null}
        </CardHeader>
        <CardContent className="space-y-4">
          {isEdit && !replaceConfig && challenge ? (
            <>
              <ul className="divide-y divide-line rounded-xl border border-line">
                {challenge.evaluation.map((check) => (
                  <li
                    key={check.id}
                    className={cn(
                      "flex items-start justify-between gap-4 px-4 py-3",
                      !check.enabled && "opacity-55",
                    )}
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-ink">{check.description}</p>
                      <p className="mt-0.5 font-mono text-xs text-faint">
                        {check.id} · {check.type}
                        {check.required ? " · required" : ""}
                      </p>
                    </div>
                    <span className="shrink-0 text-sm font-semibold text-ink tabular-nums">
                      {check.points}
                      <span className="text-xs font-normal text-faint"> pts</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-faint">
                Check parameters are not exposed by the API for existing challenges — switch on
                “Replace” to rebuild the configuration from scratch (parameters reset to defaults).
              </p>
            </>
          ) : (
            <>
              {isEdit ? (
                <Alert tone="warning" title="Rebuilding the configuration">
                  All checks will be replaced with the ones below when you save. Parameters for
                  existing checks are reset to defaults — review every field.
                </Alert>
              ) : null}

              {checks.map((check, index) => (
                <CheckEditorCard
                  key={check.key}
                  check={check}
                  index={index}
                  onChange={(next) =>
                    setChecks((previous) =>
                      previous.map((item) => (item.key === next.key ? next : item)),
                    )
                  }
                  onRemove={() =>
                    setChecks((previous) => previous.filter((item) => item.key !== check.key))
                  }
                />
              ))}

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setChecks((previous) => [...previous, makeCheck()])}
                >
                  <Plus aria-hidden />
                  Add check
                </Button>
                {checks.length === 0 ? (
                  <Button variant="ghost" size="sm" onClick={() => setChecks(starterChecks())}>
                    <ListPlus aria-hidden />
                    Use starter set
                  </Button>
                ) : null}
              </div>

              {submitted && checkProblems.length > 0 ? (
                <Alert tone="danger" title="Fix the evaluation configuration">
                  <ul className="list-inside list-disc space-y-0.5">
                    {checkProblems.map((problem) => (
                      <li key={problem}>{problem}</li>
                    ))}
                  </ul>
                </Alert>
              ) : (
                <p className="flex items-center gap-1.5 text-xs text-faint">
                  <CheckCircle2 className="size-3.5 text-success" aria-hidden />
                  Allocation must not exceed the challenge maximum of {maxPointsNumber} points.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
        <Link to="/staff/challenges" className={buttonClasses({ variant: "ghost" })}>
          Cancel
        </Link>
        {isEdit && challenge ? (
          <Link
            to={`/challenges/${challenge.slug}`}
            className={buttonClasses({ variant: "secondary" })}
          >
            View public page
          </Link>
        ) : null}
        <Button size="lg" loading={saveMutation.isPending} onClick={handleSubmit}>
          {isEdit ? "Save changes" : "Create challenge"}
        </Button>
      </div>
    </div>
  );
}
