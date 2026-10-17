import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleAlert, Link2, Plus, Send, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "sonner";

import { createSubmission } from "@/api/submissions";
import type { SubmissionCreatePayload } from "@/api/types";
import { GitHubIcon } from "@/components/common/github-icon";
import { DifficultyBadge, TrackChip } from "@/components/domain/indicators";
import { Alert, ErrorState } from "@/components/ui/feedback";
import { Button, buttonClasses } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/layout/page-container";
import { usePageTitle } from "@/hooks/use-page-title";
import { useChallenge } from "@/hooks/queries";
import { isHttpUrl, parseRepoUrl } from "@/lib/repo";
import { qk } from "@/lib/query-keys";
import { formatNumber } from "@/lib/utils";

const MAX_EVIDENCE_LINKS = 5;

interface EvidenceLink {
  key: number;
  value: string;
}

let evidenceKeySeed = 0;

export function ChallengeSubmitPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const challengeQuery = useChallenge(slug);
  const challenge = challengeQuery.data;

  usePageTitle(challenge ? `Submit — ${challenge.title}` : "Submit");

  const [repoUrl, setRepoUrl] = useState("");
  const [repoTouched, setRepoTouched] = useState(false);
  const [notes, setNotes] = useState("");
  const [evidenceLinks, setEvidenceLinks] = useState<EvidenceLink[]>([]);

  const repoParse = useMemo(() => parseRepoUrl(repoUrl), [repoUrl]);
  const repoValid = Boolean(repoParse.ref);

  const evidenceErrors = useMemo(() => {
    const errors: Record<number, string> = {};
    const seen = new Map<string, number>();
    for (const link of evidenceLinks) {
      const trimmed = link.value.trim();
      if (!trimmed) continue;
      if (!isHttpUrl(trimmed)) {
        errors[link.key] = "Must be a full http(s) URL.";
        continue;
      }
      const normalized = trimmed.toLowerCase();
      if (seen.has(normalized)) {
        errors[link.key] = "Duplicate link.";
      } else {
        seen.set(normalized, link.key);
      }
    }
    return errors;
  }, [evidenceLinks]);

  const evidenceValid = Object.keys(evidenceErrors).length === 0;

  const mutation = useMutation({
    mutationFn: (payload: SubmissionCreatePayload) => {
      if (!challenge) throw new Error("Challenge not loaded");
      return createSubmission(challenge.id, payload);
    },
    onSuccess: (submission) => {
      queryClient.setQueryData(qk.submissions.detail(submission.id), submission);
      void queryClient.invalidateQueries({ queryKey: qk.submissions.all });
      toast.success("Submission created — the evaluation will start automatically.");
      navigate(`/submissions/${submission.id}`);
    },
  });

  if (challengeQuery.isPending) {
    return (
      <PageContainer className="max-w-3xl py-10">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="mt-6 h-64 w-full" />
      </PageContainer>
    );
  }

  if (challengeQuery.isError || !challenge) {
    return (
      <PageContainer className="py-16">
        <ErrorState
          error={challengeQuery.error ?? new Error("Challenge not found.")}
          onRetry={() => challengeQuery.refetch()}
        />
      </PageContainer>
    );
  }

  function handleSubmit() {
    setRepoTouched(true);
    if (!repoValid || !evidenceValid || !challenge || mutation.isPending) return;
    const evidence = evidenceLinks
      .map((link) => link.value.trim())
      .filter((value) => value.length > 0);
    mutation.mutate({
      repo_url: repoUrl.trim(),
      notes: notes.trim() ? notes.trim() : null,
      evidence_urls: evidence,
    });
  }

  const enabledChecks = challenge.evaluation.filter((check) => check.enabled);
  const allocatedPoints = enabledChecks.reduce((total, check) => total + check.points, 0);

  return (
    <PageContainer className="max-w-4xl animate-fade-in py-8 sm:py-10">
      <Link
        to={`/challenges/${challenge.slug}`}
        className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        Back to challenge
      </Link>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <TrackChip track={challenge.track} />
        <DifficultyBadge difficulty={challenge.difficulty} />
      </div>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        Submit your build
      </h1>
      <p className="mt-2 max-w-2xl text-sm text-muted">
        For <span className="font-medium text-ink">{challenge.title}</span> · up to{" "}
        {formatNumber(challenge.max_points)} points.
      </p>

      <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <Card>
            <CardHeader>
              <CardTitle>Submission details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Field
                label="GitHub repository URL"
                htmlFor="repo-url"
                required
                error={repoTouched && !repoValid ? repoParse.error : null}
                hint="Must be a public repository on github.com."
              >
                <Input
                  id="repo-url"
                  value={repoUrl}
                  onChange={(event) => setRepoUrl(event.target.value)}
                  onBlur={() => setRepoTouched(true)}
                  placeholder="https://github.com/owner/repo"
                  invalid={repoTouched && !repoValid}
                  spellCheck={false}
                  autoComplete="off"
                />
              </Field>

              {repoValid && repoParse.ref ? (
                <div className="flex items-center gap-2 rounded-lg border border-line bg-surface-2/60 px-3.5 py-2.5 text-sm">
                  <GitHubIcon className="size-4 text-muted" aria-hidden />
                  <span className="font-mono text-ink">
                    {repoParse.ref.owner}/{repoParse.ref.repo}
                  </span>
                  <span className="ml-auto text-xs text-faint">Looks good</span>
                </div>
              ) : null}

              <Field
                label="Notes for reviewers"
                htmlFor="notes"
                hint={`${notes.length}/4000 characters — optional context the automated checks cannot see.`}
              >
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value.slice(0, 4000))}
                  placeholder="What did you build? Anything the evaluator should know?"
                  rows={5}
                />
              </Field>

              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink">Evidence links</span>
                  <span className="text-xs text-faint">
                    {evidenceLinks.length}/{MAX_EVIDENCE_LINKS}
                  </span>
                </div>
                {evidenceLinks.map((link, index) => (
                  <div key={link.key} className="flex items-start gap-2">
                    <div className="flex-1">
                      <Input
                        value={link.value}
                        onChange={(event) =>
                          setEvidenceLinks((previous) =>
                            previous.map((item) =>
                              item.key === link.key ? { ...item, value: event.target.value } : item,
                            ),
                          )
                        }
                        placeholder="https://… (demo video, deployment, screenshots)"
                        invalid={Boolean(evidenceErrors[link.key])}
                        aria-label={`Evidence link ${index + 1}`}
                        spellCheck={false}
                      />
                      {evidenceErrors[link.key] ? (
                        <p className="mt-1 text-xs text-danger">{evidenceErrors[link.key]}</p>
                      ) : null}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove evidence link ${index + 1}`}
                      onClick={() =>
                        setEvidenceLinks((previous) =>
                          previous.filter((item) => item.key !== link.key),
                        )
                      }
                    >
                      <Trash2 aria-hidden />
                    </Button>
                  </div>
                ))}
                {evidenceLinks.length < MAX_EVIDENCE_LINKS ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      setEvidenceLinks((previous) => [
                        ...previous,
                        { key: (evidenceKeySeed += 1), value: "" },
                      ])
                    }
                  >
                    <Plus aria-hidden />
                    Add link
                  </Button>
                ) : null}
              </div>

              {mutation.isError ? (
                <Alert tone="danger" icon={<CircleAlert aria-hidden />} title="Submission failed">
                  {mutation.error instanceof Error
                    ? mutation.error.message
                    : "Something went wrong. Please try again."}
                </Alert>
              ) : null}
            </CardContent>
          </Card>

          <div className="mt-6 flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
            <Link
              to={`/challenges/${challenge.slug}`}
              className={buttonClasses({ variant: "ghost" })}
            >
              Cancel
            </Link>
            <Button
              size="lg"
              loading={mutation.isPending}
              disabled={!repoValid || !evidenceValid}
              onClick={handleSubmit}
            >
              <Send aria-hidden />
              Submit for evaluation
            </Button>
          </div>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader className="py-3.5">
              <CardTitle className="text-sm">Before you submit</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted">
              <p className="flex gap-2.5">
                <Link2 className="mt-0.5 size-4 shrink-0 text-faint" aria-hidden />
                The repository must be <span className="text-ink">public</span> — the evaluator
                reads it through the GitHub API without your credentials.
              </p>
              <p className="flex gap-2.5">
                <Link2 className="mt-0.5 size-4 shrink-0 text-faint" aria-hidden />
                Point it at the repository <span className="text-ink">root</span>, not a branch or
                folder URL.
              </p>
              <p className="flex gap-2.5">
                <Link2 className="mt-0.5 size-4 shrink-0 text-faint" aria-hidden />
                Add evidence links for anything the checks cannot verify automatically.
              </p>
            </CardContent>
          </Card>

          {enabledChecks.length > 0 ? (
            <Card>
              <CardHeader className="py-3.5">
                <div>
                  <CardTitle className="text-sm">Scoring breakdown</CardTitle>
                  <p className="mt-0.5 text-xs text-faint">
                    {allocatedPoints < challenge.max_points
                      ? `${formatNumber(allocatedPoints)} of ${formatNumber(challenge.max_points)} points allocated`
                      : `${formatNumber(allocatedPoints)} points available`}
                  </p>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-line">
                  {enabledChecks.map((check) => (
                    <li
                      key={check.id}
                      className="flex items-start justify-between gap-3 px-5 py-2.5 text-sm"
                    >
                      <span className="text-muted">{check.description}</span>
                      <span className="shrink-0 font-semibold text-ink tabular-nums">
                        {check.points}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </PageContainer>
  );
}
