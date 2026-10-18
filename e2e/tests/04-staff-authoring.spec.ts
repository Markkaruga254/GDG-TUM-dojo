import { BASE_URL, SEEDED_CHALLENGE, SEEDED_DRAFT_CHALLENGE } from "../support/env";
import { expect, test } from "../support/sessions";

test("a moderator creates, publishes and exposes a new challenge", async ({
  asModerator: page,
  browser,
}) => {
  const stamp = Date.now().toString(36);
  const title = `E2E Authoring ${stamp}`;
  const slug = `e2e-authoring-${stamp}`;

  await page.goto("/staff/challenges");
  await page.getByRole("link", { name: "New challenge" }).click();
  await expect(page).toHaveURL(/\/staff\/challenges\/new$/);

  await page.locator("#challenge-title").fill(title);
  await page.locator("#challenge-slug").fill(slug);
  await page
    .locator("#challenge-description")
    .fill("Challenge created by the end-to-end suite to prove the authoring flow works.");
  await page.locator("#challenge-track").fill("e2e");

  // The starter checks (20 of 100 points) are valid as-is.
  await page.getByRole("button", { name: "Create challenge" }).click();
  await expect(page).toHaveURL(new RegExp(`/staff/challenges/${slug}/edit$`));

  // The new draft is invisible to anonymous visitors...
  const anonymous = await browser.newContext({ baseURL: BASE_URL });
  const anonymousPage = await anonymous.newPage();
  await anonymousPage.goto("/challenges");
  await expect(anonymousPage.getByText(SEEDED_CHALLENGE.title).first()).toBeVisible();
  await expect(anonymousPage.getByText(SEEDED_DRAFT_CHALLENGE.title)).toHaveCount(0);
  await expect(anonymousPage.getByText(title)).toHaveCount(0);

  // ...until the moderator publishes it.
  await page.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Published", { exact: true })).toBeVisible();

  await anonymousPage.goto(`/challenges/${slug}`);
  await expect(anonymousPage.getByRole("heading", { name: title })).toBeVisible();
  await expect(anonymousPage.getByText("Sign in to submit")).toBeVisible();

  await anonymous.close();
});
