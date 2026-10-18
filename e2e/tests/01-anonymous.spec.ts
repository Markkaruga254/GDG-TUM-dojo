import { expect, test } from "@playwright/test";

import { SEEDED_CHALLENGE, SEEDED_DRAFT_CHALLENGE, SEEDED_STUDENT2 } from "../support/env";

test.describe("anonymous browsing", () => {
  test("the catalogue lists the published challenge but never the draft", async ({ page }) => {
    await page.goto("/challenges");

    await expect(page.getByText(SEEDED_CHALLENGE.title).first()).toBeVisible();
    await expect(page.getByText(SEEDED_DRAFT_CHALLENGE.title)).toHaveCount(0);
  });

  test("the challenge detail page invites anonymous visitors to sign in", async ({ page }) => {
    await page.goto(`/challenges/${SEEDED_CHALLENGE.slug}`);

    await expect(page.getByRole("heading", { name: SEEDED_CHALLENGE.title }).first()).toBeVisible();
    await expect(page.getByText("Sign in to submit")).toBeVisible();
  });

  test("protected routes ask for sign-in instead of rendering", async ({ page }) => {
    await page.goto(`/challenges/${SEEDED_CHALLENGE.slug}/submit`);
    await expect(page.getByText("Sign in to continue")).toBeVisible();
    await expect(
      page.getByText("Sign in with GitHub to submit a repository for this challenge."),
    ).toBeVisible();

    await page.goto("/submissions");
    await expect(page.getByText("Sign in to continue")).toBeVisible();
    await expect(
      page.getByText("Sign in to see your submissions and evaluation results."),
    ).toBeVisible();
  });

  test("the leaderboard credits the seeded evaluated submission", async ({ page }) => {
    await page.goto("/leaderboard");

    await expect(page.getByText("Leaderboard").first()).toBeVisible();
    await expect(page.getByText(SEEDED_STUDENT2.displayName).first()).toBeVisible();
  });
});
