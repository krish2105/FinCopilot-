import { expect, test } from "@playwright/test";

// Marketing surfaces need no backend — a safe smoke test for staging.
test("landing shows the value prop and CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /refuses to guess/i })).toBeVisible();
  await expect(page.getByRole("link", { name: /open workspace/i }).first()).toBeVisible();
});

test("pricing lists the three plans", async ({ page }) => {
  await page.goto("/pricing");
  await expect(page.getByRole("heading", { name: /pricing that scales/i })).toBeVisible();
  for (const plan of ["Free", "Pro", "Team"]) {
    await expect(page.getByRole("heading", { name: plan, exact: true })).toBeVisible();
  }
});

test("trust page lists security controls", async ({ page }) => {
  await page.goto("/trust");
  await expect(page.getByText(/Tenant isolation \+ RLS/i)).toBeVisible();
});
