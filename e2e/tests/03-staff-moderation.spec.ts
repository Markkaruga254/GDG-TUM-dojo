import { SEEDED_CHALLENGE, SEEDED_STUDENT2 } from "../support/env";
import { expect, test } from "../support/sessions";

test("a moderator re-runs, disqualifies and reinstates a submission", async ({
  asModerator: page,
}) => {
  await page.goto("/staff/submissions");

  await page.getByLabel("Select challenge").selectOption({ label: SEEDED_CHALLENGE.title });
  const row = page
    .getByRole("listitem")
    .filter({ hasText: new RegExp(`${SEEDED_STUDENT2.displayName}|${SEEDED_STUDENT2.username}`) });
  await expect(row).toBeVisible();
  await row.getByRole("link", { name: "Review" }).click();

  await expect(page).toHaveURL(/\/submissions\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: SEEDED_CHALLENGE.title }).first()).toBeVisible();

  // Force a re-run; the attempt counter proves the evaluation executed again.
  await page.getByRole("button", { name: "Re-run evaluation (force)" }).click();
  await expect(page.getByText("2 attempts")).toBeVisible();

  // Disqualify with a reason.
  await page.getByRole("button", { name: "Disqualify submission" }).click();
  await page.getByLabel("Reason").fill("Repository is a fork of another submission.");
  await page.getByRole("dialog").getByRole("button", { name: "Disqualify", exact: true }).click();
  await expect(page.getByRole("button", { name: "Reinstate submission" })).toBeVisible();
  await expect(page.getByText("Repository is a fork of another submission.")).toBeVisible();
  await expect(page.getByText("This score does not count toward the leaderboard.")).toBeVisible();

  // Reinstate.
  await page.getByRole("button", { name: "Reinstate submission" }).click();
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: "Reinstate", exact: true })
    .click();
  await expect(page.getByRole("button", { name: "Disqualify submission" })).toBeVisible();
  await expect(page.getByText("This score counts toward the leaderboard.")).toBeVisible();
});
