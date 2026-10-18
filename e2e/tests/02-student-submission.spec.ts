import { EXPECTED_SCORE, MOCK_REPO_URL, SEEDED_CHALLENGE, SEEDED_STUDENT } from "../support/env";
import { expect, test } from "../support/sessions";

// The second test relies on the submission created by the first one.
test.describe.configure({ mode: "serial" });

test("a student submits a repository and receives a full auto-evaluated result", async ({
  asStudent: page,
}) => {
  await page.goto(`/challenges/${SEEDED_CHALLENGE.slug}/submit`);

  await page.getByLabel(/github repository url/i).fill(MOCK_REPO_URL);
  await page.getByRole("button", { name: "Add link" }).click();
  await page
    .getByLabel("Evidence link 1", { exact: true })
    .fill("https://example.com/cloud-notes-demo");
  await page.getByRole("button", { name: "Submit for evaluation" }).click();

  // The SPA lands on the fresh submission and auto-triggers the evaluation.
  await expect(page).toHaveURL(/\/submissions\/[0-9a-f-]{36}$/);
  await expect(page.getByText("Evaluation result")).toBeVisible();
  await expect(page.getByText("All required checks passed.")).toBeVisible();
  await expect(page.getByText(`of ${EXPECTED_SCORE.max} pts`)).toBeVisible();
  await expect(page.getByText("At least one evidence link.")).toBeVisible();
  await expect(page.getByText("This score counts toward the leaderboard.")).toBeVisible();
  await expect(
    page.getByText(`Evaluation complete — ${EXPECTED_SCORE.awarded} points!`),
  ).toBeVisible();
});

test("the submission appears in My submissions with a passed status", async ({
  asStudent: page,
}) => {
  await page.goto("/submissions");

  const row = page.getByRole("listitem").filter({ hasText: SEEDED_CHALLENGE.title });
  await expect(row).toBeVisible();
  await expect(row.getByText("Passed", { exact: true })).toBeVisible();
});

test("the leaderboard credits the student", async ({ asStudent: page }) => {
  await page.goto("/leaderboard");

  await expect(page.getByText(SEEDED_STUDENT.displayName).first()).toBeVisible();
});
