import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(
  readFileSync(process.env.RELEASEFENCE_BROWSER_FIXTURE!, "utf8"),
);
const views = [
  "Overview",
  "Releases",
  "Canaries",
  "Incidents",
  "Connections",
  "Audit",
  "Settings",
];
async function login(page: Page, username = "owner") {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page
    .getByLabel("Password", { exact: true })
    .fill(fixture.passwords[username]);
  await page.getByRole("button", { name: "Open release desk" }).click();
  await expect(
    page.getByRole("button", { name: `${username} · Sign out` }),
  ).toBeVisible();
}

test("login errors, keyboard submission and logout revoke the browser session", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("owner");
  await page.getByLabel("Password", { exact: true }).fill("incorrect-password");
  await page.getByLabel("Password", { exact: true }).press("Enter");
  await expect(page.getByRole("alert")).toBeVisible();
  await page
    .getByLabel("Password", { exact: true })
    .fill(fixture.passwords.owner);
  await page.getByLabel("Password", { exact: true }).press("Enter");
  await expect(
    page.getByRole("heading", { name: "Your release control room" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "owner · Sign out" }).click();
  await expect(page.getByLabel("Username", { exact: true })).toBeVisible();
  expect((await page.request.get("/api/orgs")).status()).toBe(401);
});

test("actual source-bound metrics, every navigation view and WCAG automated checks", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await login(page);
  await expect(page.getByText("10 / 10", { exact: true })).toBeVisible();
  for (const view of views) {
    await page
      .getByRole("navigation")
      .getByRole("button", { name: view, exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      view === "Overview" ? "Your release control room" : view,
    );
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      results.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
      view,
    ).toEqual([]);
  }
  expect(failures).toEqual([]);
  await page.screenshot({
    path: `${process.env.RELEASEFENCE_BROWSER_OUTPUT}/desktop.png`,
    fullPage: true,
  });
});

test("organization switching clears previous evidence and unknown cost stays unknown", async ({
  page,
}) => {
  await login(page);
  await expect(page.getByText("10 / 10", { exact: true })).toBeVisible();
  await expect(page.getByText("Unknown calls", { exact: false })).toBeVisible();
  await expect(
    page
      .locator(".mini-grid > span")
      .filter({ hasText: "USD per successful task" })
      .locator("strong"),
  ).toHaveText("—");
  await page
    .getByLabel("Organization", { exact: true })
    .selectOption(fixture.second);
  await expect(page.getByText("No measured traffic yet")).toBeVisible();
  await expect(page.getByText("10 / 10", { exact: true })).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Releases", exact: true })
    .click();
  await expect(page.getByText("No release bundles registered.")).toBeVisible();
});

test("independent reviewer cannot mutate owner resources or read another organization", async ({
  page,
}) => {
  await login(page, "reviewer");
  await expect(
    page.getByLabel("Organization", { exact: true }).getByRole("option"),
  ).toHaveCount(2);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Releases", exact: true })
    .click();
  await expect(
    page.getByText("Owner or release operator access required."),
  ).toBeVisible();
  await expect(page.getByLabel("Release manifest JSON")).toHaveCount(0);
  expect(
    (await page.request.get(`/api/orgs/${fixture.second}/release`)).status(),
  ).toBe(403);
});

test("canary setup selects OSS profile explicitly and mobile layout fits", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Canaries", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", {
      name: "Required trace backends",
      exact: true,
    }),
  ).toHaveValue("mlflow-phoenix-v1");
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Settings", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Settings");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Overview", exact: true })
    .click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `${process.env.RELEASEFENCE_BROWSER_OUTPUT}/mobile.png`,
    fullPage: true,
  });
});

test("owner creates a canary, independent reviewer approves and dispatch remains unverified", async ({
  page,
  browser,
}) => {
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Canaries", exact: true })
    .click();
  await page.getByLabel("Stable digest", { exact: true }).fill(fixture.stable);
  await page
    .getByLabel("Candidate digest", { exact: true })
    .fill(fixture.candidate);
  await page
    .getByLabel("Enrollment IDs (comma separated)", { exact: true })
    .fill(fixture.enrollment);
  await page
    .getByRole("button", { name: "Save configuration", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Start / expand canary", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", {
      name: "Approve canary + manual rollback",
      exact: true,
    }),
  ).toHaveCount(0);
  const reviewContext = await browser.newContext({
    baseURL: process.env.RELEASEFENCE_BROWSER_URL,
  });
  try {
    const review = await reviewContext.newPage();
    await login(review, "reviewer");
    await review
      .getByRole("navigation")
      .getByRole("button", { name: "Canaries", exact: true })
      .click();
    review.once("dialog", (d) => d.accept());
    await review
      .getByRole("button", {
        name: "Approve canary + manual rollback",
        exact: true,
      })
      .click();
    await expect(review.locator(".receipt")).toBeVisible();
    await page
      .getByRole("button", { name: "Refresh data", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Start / expand canary", exact: true }),
    ).toBeEnabled();
    page.once("dialog", (d) => d.accept());
    await page
      .getByRole("button", { name: "Start / expand canary", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Promote candidate", exact: true }),
    ).toBeDisabled();
    const rolls = await (
      await page.request.get(`/api/orgs/${fixture.first}/rollout`)
    ).json();
    expect(rolls[0].state).not.toBe("canary_running");
    const commands = await (
      await page.request.get(`/api/orgs/${fixture.first}/command`)
    ).json();
    expect(commands).toHaveLength(1);
    expect(commands[0].state).not.toBe("verified");
  } finally {
    await reviewContext.close();
  }
});
