import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Calculator,
  ExternalLink,
  FileWarning,
  Link2,
  RefreshCw,
  ShieldBan,
  ShieldCheck,
  Timer,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import {
  clearSubmissionScoreOverride,
  disqualifySubmission,
  overrideSubmissionScore,
  reinstateSubmission,
} from "@/api/admin";
import { evaluateSubmission } from "@/api/submissions";
import type { CheckResultOut, SubmissionResults } from "@/api/types";
import { GitHubIcon } from "@/components/common/github-icon";
import {
  CheckStatusBadge,
  DisqualifiedBadge,
  OverrideBadge,
  SubmissionStatusBadge,
} from "@/components/domain/indicators";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, EmptyState, Spinner } from "@/components/ui/feedback";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { ProgressRing } from "@/components/ui/progress-ring";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/layout/page-container";
import { useSession } from "@/hooks/use-auth";
import { usePageTitle } from "@/hooks/use-page-title";
import { useSubmissionResults } from "@/hooks/queries";
import { qk } from "@/lib/query-keys";
import { buttonClasses } from "@/components/ui/button";
import { cn, formatDateTime, formatNumber, formatRelative } from "@/lib/utils";

const ACTIVE_STATUSES = ["pending", "queued", "running"];

function formatEvidenceValue(value: unknown): string {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function CheckResultRow({ check }: { check: CheckResultOut }) {
  const evidenceEntries = Object.entries(check.evidence ?? {});

  return (
    <li className="px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-ink">{check.description}</span>
            <CheckStatusBadge status={check.status} />
          </div>
          <p className="mt-1 text-sm text-muted">{check.message}</p>
          <code className="mt-1.5 inline-block rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-faint">
            {check.type}
          </code>
          {evidenceEntries.length > 0 ? (
            <details className="group mt-2">
              <summary className="cursor-pointer text-xs text-faint transition-colors select-none hover:text-muted">
                Evidence
              </summary>
              <dl className="mt-2 space-y-1 rounded-lg border border-line bg-surface-2/60 p-3 font-mono text-xs">
                {evidenceEntries.map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <dt className="shrink-0 text-faint">{key}:</dt>
                    <dd className="break-all text-muted">{formatEvidenceValue(value)}</dd>
                  </div>
                ))}
              </dl>
            </details>
          ) : null}
        </div>
        <span className="shrink-0 text-sm font-semibold text-ink tabular-nums">
          {check.awarded_points}
          <span className="text-xs font-normal text-faint">/{check.max_points}</span>
        </span>
      </div>
    </li>
  );
}

function EvaluationPanel({
  results,
  onEvaluate,
  evaluating,
  evaluateError,
}: {
  results: SubmissionResults;
  onEvaluate: () => void;
  evaluating: boolean;
  evaluateError: Error | null;
}) {
  const { submission, evaluation } = results;

  if (!evaluation) {
    if (ACTIVE_STATUSES.includes(submission.status) || evaluating) {
      return (
        <Card>
          <CardContent className="flex flex-col items-center px-6 py-12 text-center">
            <Spinner className="size-6 text-primary" />
            <h3 className="mt-4 text-sm font-semibold text-ink">Evaluation in progress</h3>
            <p className="mt-1 max-w-sm text-sm text-muted">
              The evaluator is inspecting{" "}
              <span className="font-mono">{submission.repo_full_name}</span> through the GitHub API.
              This page refreshes automatically.
            </p>
            {evaluateError ? (
              <Alert
                tone="danger"
                title="Could not start the evaluation"
                className="mt-6 w-full text-left"
              >
                {evaluateError.message}
              </Alert>
            ) : null}
          </CardContent>
        </Card>
      );
    }
    return (
      <Card>
        <CardContent className="flex flex-col items-center px-6 py-12 text-center">
          <FileWarning className="size-6 text-warning" aria-hidden />
          <h3 className="mt-4 text-sm font-semibold text-ink">No evaluation recorded</h3>
          <p className="mt-1 max-w-sm text-sm text-muted">
            This submission has no evaluation result yet. You can trigger one below.
          </p>
          {evaluateError ? (
            <Alert
              tone="danger"
              title="Evaluation failed to start"
              className="mt-6 w-full text-left"
            >
              {evaluateError.message}
            </Alert>
          ) : null}
          <Button className="mt-6" loading={evaluating} onClick={onEvaluate}>
            <RefreshCw aria-hidden />
            Run evaluation
          </Button>
        </CardContent>
      </Card>
    );
  }

  const tone =
    evaluation.status === "error"
      ? "danger"
      : evaluation.awarded_score >= evaluation.max_score && evaluation.max_score > 0
        ? "success"
        : "primary";

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Evaluation result</CardTitle>
          <p className="mt-0.5 text-sm text-muted">
            {evaluation.status === "completed"
              ? `Completed ${formatRelative(evaluation.completed_at ?? evaluation.started_at)}`
              : evaluation.status === "running"
                ? "Currently running…"
                : "The evaluation run hit an error."}
          </p>
        </div>
        <span className="font-mono text-xs text-faint">v{evaluation.evaluator_version}</span>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-6 border-b border-line py-8 sm:flex-row sm:justify-center sm:gap-10">
        <ProgressRing value={evaluation.awarded_score} max={evaluation.max_score} tone={tone}>
          <span className="text-3xl font-semibold tracking-tight text-ink tabular-nums">
            {formatNumber(evaluation.awarded_score)}
          </span>
          <span className="text-xs text-faint">of {formatNumber(evaluation.max_score)} pts</span>
        </ProgressRing>
        <div className="max-w-sm text-center sm:text-left">
          {evaluation.feedback ? (
            <p className="text-sm text-muted">{evaluation.feedback}</p>
          ) : (
            <p className="text-sm text-muted">
              {evaluation.checks.filter((check) => check.status === "passed").length} of{" "}
              {evaluation.checks.length} checks passed.
            </p>
          )}
          {results.effective_points !== evaluation.awarded_score ? (
            <p className="mt-3 text-sm">
              <span className="text-faint">Effective score: </span>
              <span className="font-semibold text-ink">
                {formatNumber(results.effective_points)} pts
              </span>
              {submission.is_disqualified ? (
                <span className="text-danger"> · disqualified</span>
              ) : null}
            </p>
          ) : null}
          <p
            className={cn(
              "mt-3 inline-flex items-center gap-1.5 text-xs",
              results.counts_for_leaderboard ? "text-success" : "text-faint",
            )}
          >
            {results.counts_for_leaderboard
              ? "This score counts toward the leaderboard."
              : "This score does not count toward the leaderboard."}
          </p>
        </div>
      </CardContent>
      <CardContent className="p-0">
        <ul className="divide-y divide-line">
          {evaluation.checks.map((check) => (
            <CheckResultRow key={check.id} check={check} />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

type StaffAction =
  | { kind: "disqualify"; reason: string }
  | { kind: "reinstate" }
  | { kind: "override"; points: number; reason: string }
  | { kind: "clear-override" };

function StaffActions({ results }: { results: SubmissionResults }) {
  const { isAdmin } = useSession();
  const queryClient = useQueryClient();
  const { submission } = results;

  const [disqualifyOpen, setDisqualifyOpen] = useState(false);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [reinstateOpen, setReinstateOpen] = useState(false);
  const [clearOverrideOpen, setClearOverrideOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [overridePoints, setOverridePoints] = useState(String(submission.effective_points || ""));

  const mutation = useMutation({
    mutationFn: (action: StaffAction) => {
      switch (action.kind) {
        case "disqualify":
          return disqualifySubmission(submission.id, { reason: action.reason });
        case "reinstate":
          return reinstateSubmission(submission.id);
        case "override":
          return overrideSubmissionScore(submission.id, {
            points: action.points,
            reason: action.reason,
          });
        case "clear-override":
          return clearSubmissionScoreOverride(submission.id);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.submissions.results(submission.id) });
      void queryClient.invalidateQueries({ queryKey: qk.submissions.detail(submission.id) });
      void queryClient.invalidateQueries({ queryKey: qk.submissions.all });
      void queryClient.invalidateQueries({ queryKey: qk.leaderboard.all });
      void queryClient.invalidateQueries({ queryKey: ["staff"] });
      toast.success("Moderation action applied.");
      setDisqualifyOpen(false);
      setOverrideOpen(false);
      setReinstateOpen(false);
      setClearOverrideOpen(false);
      setReason("");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Action failed."),
  });

  const evaluate = useMutation({
    mutationFn: () => evaluateSubmission(submission.id, { force: true }),
    onSuccess: (data) => {
      queryClient.setQueryData(qk.submissions.results(submission.id), data);
      void queryClient.invalidateQueries({ queryKey: qk.leaderboard.all });
      toast.success("Evaluation re-run complete.");
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Re-run failed."),
  });

  return (
    <Card>
      <CardHeader className="py-3.5">
        <CardTitle className="text-sm">Staff actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5">
        <Button
          variant="secondary"
          className="w-full justify-start"
          loading={evaluate.isPending}
          onClick={() => evaluate.mutate()}
        >
          <RefreshCw aria-hidden />
          Re-run evaluation (force)
        </Button>

        {submission.is_disqualified ? (
          <Button
            variant="secondary"
            className="w-full justify-start text-success [&_svg]:text-success"
            onClick={() => setReinstateOpen(true)}
          >
            <ShieldCheck aria-hidden />
            Reinstate submission
          </Button>
        ) : (
          <Button
            variant="secondary"
            className="w-full justify-start text-danger [&_svg]:text-danger"
            onClick={() => setDisqualifyOpen(true)}
          >
            <ShieldBan aria-hidden />
            Disqualify submission
          </Button>
        )}

        {isAdmin ? (
          submission.score_override_points !== null ? (
            <Button
              variant="secondary"
              className="w-full justify-start"
              onClick={() => setClearOverrideOpen(true)}
            >
              <Calculator aria-hidden />
              Clear score override
            </Button>
          ) : (
            <Button
              variant="secondary"
              className="w-full justify-start"
              onClick={() => {
                setOverridePoints(String(submission.effective_points || ""));
                setOverrideOpen(true);
              }}
            >
              <Calculator aria-hidden />
              Override score
            </Button>
          )
        ) : null}
      </CardContent>

      {/* Disqualify */}
      <Dialog open={disqualifyOpen} onOpenChange={setDisqualifyOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Disqualify submission</DialogTitle>
            <DialogDescription>
              The score stops counting toward leaderboards and badges. The reason is recorded in the
              audit trail.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field label="Reason" htmlFor="disqualify-reason" required>
              <Textarea
                id="disqualify-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value.slice(0, 500))}
                placeholder="e.g. Repository is a fork of another submission."
                rows={3}
              />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDisqualifyOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={mutation.isPending}
              disabled={reason.trim().length < 5}
              onClick={() => mutation.mutate({ kind: "disqualify", reason: reason.trim() })}
            >
              Disqualify
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Override score */}
      <Dialog open={overrideOpen} onOpenChange={setOverrideOpen}>
        <DialogContent size="sm">
          <DialogHeader>
            <DialogTitle>Override score</DialogTitle>
            <DialogDescription>
              Sets a manual effective score (0–10000) that takes precedence over the automated
              result until cleared.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <Field label="Points" htmlFor="override-points" required>
              <Input
                id="override-points"
                type="number"
                min={0}
                max={10000}
                value={overridePoints}
                onChange={(event) => setOverridePoints(event.target.value)}
              />
            </Field>
            <Field label="Reason" htmlFor="override-reason" required>
              <Textarea
                id="override-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value.slice(0, 500))}
                placeholder="Why the score is being adjusted."
                rows={3}
              />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOverrideOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={mutation.isPending}
              disabled={
                reason.trim().length < 5 ||
                !Number.isInteger(Number(overridePoints)) ||
                Number(overridePoints) < 0 ||
                Number(overridePoints) > 10000
              }
              onClick={() =>
                mutation.mutate({
                  kind: "override",
                  points: Number(overridePoints),
                  reason: reason.trim(),
                })
              }
            >
              Save override
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reinstate */}
      <AlertDialog open={reinstateOpen} onOpenChange={setReinstateOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>Reinstate submission?</AlertDialogTitle>
          <AlertDialogDescription>
            The submission starts counting again for leaderboards and badges.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-primary text-primary-fg hover:bg-primary-hover"
              onClick={() => mutation.mutate({ kind: "reinstate" })}
            >
              Reinstate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Clear override */}
      <AlertDialog open={clearOverrideOpen} onOpenChange={setClearOverrideOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>Clear score override?</AlertDialogTitle>
          <AlertDialogDescription>
            The submission reverts to its automated evaluation score.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-primary text-primary-fg hover:bg-primary-hover"
              onClick={() => mutation.mutate({ kind: "clear-override" })}
            >
              Clear override
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

export function SubmissionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { isStaff } = useSession();
  const resultsQuery = useSubmissionResults(id);
  const results = resultsQuery.data;

  usePageTitle(results ? `Submission — ${results.challenge_title}` : "Submission");

  const evaluate = useMutation({
    mutationFn: () => evaluateSubmission(id as string),
    onSuccess: (data) => {
      queryClient.setQueryData(qk.submissions.results(id as string), data);
      void queryClient.invalidateQueries({ queryKey: qk.submissions.all });
      void queryClient.invalidateQueries({ queryKey: qk.leaderboard.all });
      void queryClient.invalidateQueries({ queryKey: qk.badges.all });
      toast.success(
        data.submission.status === "passed"
          ? `Evaluation complete — ${data.effective_points} points!`
          : "Evaluation complete.",
      );
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Could not start the evaluation.");
    },
  });

  const autoTriggered = useRef(false);

  useEffect(() => {
    if (autoTriggered.current || !results) return;
    const { submission } = results;
    if (
      submission.status === "pending" &&
      submission.evaluation_attempts === 0 &&
      !submission.is_disqualified
    ) {
      // First visit after creating a submission — kick off evaluation exactly
      // once; the ref guard makes later poll updates no-ops. `mutate` is
      // referentially stable in react-query v5.
      autoTriggered.current = true;
      evaluate.mutate();
    }
  }, [results, evaluate]);

  if (resultsQuery.isPending) {
    return (
      <PageContainer className="py-8 sm:py-10">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="mt-5 h-8 w-2/3" />
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_340px]">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </PageContainer>
    );
  }

  if (resultsQuery.isError || !results) {
    return (
      <PageContainer className="py-16">
        <EmptyState
          title="Submission not found"
          description="It may have been removed, or you do not have access to it."
          action={
            <Link to="/submissions" className={buttonClasses({ variant: "secondary" })}>
              Back to my submissions
            </Link>
          }
        />
      </PageContainer>
    );
  }

  const { submission } = results;

  return (
    <PageContainer className="animate-fade-in py-8 sm:py-10">
      <Link
        to="/submissions"
        className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        My submissions
      </Link>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <SubmissionStatusBadge status={submission.status} />
        {submission.is_disqualified ? <DisqualifiedBadge /> : null}
        {submission.score_override_points !== null && !submission.is_disqualified ? (
          <OverrideBadge points={submission.score_override_points} />
        ) : null}
      </div>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        <Link
          to={`/challenges/${results.challenge_slug}`}
          className="transition-colors hover:text-primary"
        >
          {results.challenge_title}
        </Link>
      </h1>
      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-faint">
        <a
          href={submission.repo_url}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1.5 font-mono transition-colors hover:text-ink"
        >
          <GitHubIcon className="size-3.5" aria-hidden />
          {submission.repo_full_name}
          <ExternalLink className="size-3" aria-hidden />
        </a>
        <span>Submitted {formatDateTime(submission.submitted_at)}</span>
        {submission.evaluated_at ? (
          <span>Evaluated {formatDateTime(submission.evaluated_at)}</span>
        ) : null}
        <span className="inline-flex items-center gap-1.5">
          <Timer className="size-3.5" aria-hidden />
          {submission.evaluation_attempts}{" "}
          {submission.evaluation_attempts === 1 ? "attempt" : "attempts"}
        </span>
      </div>

      {submission.is_disqualified && submission.disqualification_reason ? (
        <Alert tone="danger" title="Disqualified" className="mt-6">
          {submission.disqualification_reason}
        </Alert>
      ) : null}
      {submission.score_override_points !== null ? (
        <Alert tone="info" title="Manual score override" className="mt-6">
          Effective score set to {formatNumber(submission.score_override_points)} points
          {submission.score_override_reason ? ` — ${submission.score_override_reason}` : ""}.
        </Alert>
      ) : null}

      <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_340px]">
        <div className="min-w-0">
          <EvaluationPanel
            results={results}
            onEvaluate={() => evaluate.mutate()}
            evaluating={evaluate.isPending}
            evaluateError={evaluate.isError ? (evaluate.error as Error) : null}
          />
        </div>

        <div className="min-w-0 space-y-4">
          <Card>
            <CardHeader className="py-3.5">
              <CardTitle className="text-sm">Submission</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              {submission.notes ? (
                <div>
                  <p className="text-xs font-medium tracking-wide text-faint uppercase">Notes</p>
                  <p className="mt-1.5 leading-relaxed whitespace-pre-line text-muted">
                    {submission.notes}
                  </p>
                </div>
              ) : null}
              <div>
                <p className="text-xs font-medium tracking-wide text-faint uppercase">
                  Evidence links
                </p>
                {submission.evidence_urls.length > 0 ? (
                  <ul className="mt-1.5 space-y-1.5">
                    {submission.evidence_urls.map((url) => (
                      <li key={url}>
                        <a
                          href={url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex max-w-full items-center gap-1.5 text-primary hover:underline"
                        >
                          <Link2 className="size-3.5 shrink-0" aria-hidden />
                          <span className="truncate text-xs">{url}</span>
                        </a>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1.5 text-muted">None provided.</p>
                )}
              </div>
            </CardContent>
          </Card>

          {isStaff ? <StaffActions results={results} /> : null}
        </div>
      </div>
    </PageContainer>
  );
}
