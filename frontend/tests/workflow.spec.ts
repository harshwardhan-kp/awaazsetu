import { test, expect } from "@playwright/test";
const incident = {
  id: "inc-1",
  ticket_id: "AWS-TEST",
  summary: "People need help near a landmark",
  incident_type: "rescue",
  status: "new",
  severity_score: 65,
  severity_band: "high",
  severity_reasons: [{ label: "Rescue needed", points: 40 }],
  latitude: 18.51,
  longitude: 73.85,
  location_name: "Test landmark",
  location_method: "gazetteer",
  location_confidence: 0.7,
  ward: "Test ward",
  needs_clarification: false,
  report_count: 1,
  unique_reporters: 1,
  languages: ["mr"],
  channels: ["web"],
  created_at: "2026-10-01T01:00:00Z",
  updated_at: "2026-10-01T01:00:00Z",
  reports: [
    {
      id: "r1",
      text: "We need help at our home",
      language: "mr",
      channel: "web",
      created_at: "2026-10-01T01:00:00Z",
      extraction_method: "rules",
    },
  ],
  history: [],
};
test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: any = {};
    if (path.endsWith("/health")) json = { demo: true };
    else if (path.endsWith("/auth/login"))
      json = { token: "test-token", expires_in: 3600 };
    else if (path === "/api/reports")
      json = {
        ticket_id: "AWS-TEST",
        tracking_token: "private-token",
        acknowledgement: "Report received",
      };
    else if (path.startsWith("/api/track/"))
      json = {
        ticket_id: "AWS-TEST",
        status: "new",
        acknowledgement: "Report received",
        needs_clarification: true,
        clarification_prompt: "Name a nearby landmark",
        updates: [],
      };
    else if (path === "/api/incidents") json = { items: [incident], total: 1 };
    else if (path === "/api/incidents/inc-1")
      json = {
        ...incident,
        status: route.request().method() === "PATCH" ? "verified" : "new",
      };
    else if (path === "/api/coverage")
      json = {
        total_reports: 1,
        total_incidents: 1,
        unique_reporters: 1,
        by_language: [{ label: "mr", count: 1 }],
        by_channel: [{ label: "web", count: 1 }],
        wards: [
          {
            ward: "Test ward",
            reports: 1,
            expected_reports: null,
            gap_index: null,
          },
        ],
        baseline_note: "No validated baseline",
      };
    else if (path === "/api/outbox") json = { items: [], total: 0 };
    else if (path === "/api/alerts") json = { queued: 0 };
    else if (path === "/api/settings")
      json = {
        demo: true,
        integrations: [
          { name: "SMS", configured: false, description: "SIM setup required" },
        ],
        gazetteer_count: 10,
        baseline_note: "No validated baseline",
      };
    else if (path === "/api/demo/seed") json = { reports: 1, incidents: 1 };
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(json),
    });
  });
});
test("resident language, report receipt and private tracking", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("अहवालाची भाषा").selectOption("en");
  await page
    .getByLabel("Describe the situation")
    .fill("People trapped in chest deep water near Test landmark");
  await page.getByLabel("I agree to share").check();
  await page.getByRole("button", { name: "Send report", exact: true }).click();
  await expect(page.getByText("Your voice has been received")).toBeVisible();
  await page.getByRole("link", { name: "Track your report" }).click();
  await expect(page.getByText("A little more detail helps.")).toBeVisible();
  await page.getByLabel("Nearby landmark or address").fill("Test landmark");
  await page.getByRole("button", { name: "Send clarification" }).click();
  await expect(page.getByRole("heading", { name: "AWS-TEST" })).toBeVisible();
});
test("coordinator reviews source, verifies and browses operational modules", async ({
  page,
}) => {
  await page.goto("/console");
  await page.getByLabel("Coordinator password").fill("not-a-real-password");
  await page.getByRole("button", { name: "Enter console" }).click();
  await page.screenshot({
    path: "test-results/console-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: incident.summary }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("We need help at our home")).toBeVisible();
  await page.getByLabel("Notes", { exact: true }).fill("Verified in test");
  const patch = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/incidents/inc-1") &&
      r.request().method() === "PATCH",
  );
  await page.getByRole("button", { name: "verified", exact: true }).click();
  await patch;
  await expect(
    page.getByRole("button", { name: "verified", exact: true }),
  ).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("link", { name: "Coverage", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ward coverage" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Notifications", exact: true }).click();
  await page.getByLabel("Ward / area").fill("Test ward");
  await page.getByLabel("Message", { exact: true }).fill("Drill update only");
  await page.getByRole("button", { name: "Queue alert" }).click();
  await expect(
    page.getByText("Alert queued for 0 opted-in recipients."),
  ).toBeVisible();
  await page.getByRole("link", { name: "System & settings" }).click();
  await expect(page.getByText("Not configured", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Load drill examples" }).click();
  await expect(
    page.getByText("Drill dataset ready: 1 reports and 1 incidents."),
  ).toBeVisible();
});
for (const width of [390, 768, 1440])
  test(`resident layout fits ${width}px viewport`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: "अहवाल पाठवा", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: `test-results/resident-${width}.png`,
      fullPage: true,
    });
  });

test("voice preview requires consent and review, submits edited text once", async ({
  page,
}) => {
  let previews = 0;
  await page.route("**/api/transcriptions", async (route) => {
    previews++;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ text: "Water near the landmark", language: "en" }),
    });
  });
  await page.goto("/");
  await page.getByLabel("अहवालाची भाषा").selectOption("en");
  await page
    .locator("input[type=file]")
    .setInputFiles({
      name: "voice.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("test audio fixture"),
    });
  await expect(
    page.getByRole("button", { name: "Transcribe and review" }),
  ).toBeDisabled();
  await page.getByLabel("I agree to share").check();
  await page.getByRole("button", { name: "Transcribe and review" }).click();
  await expect(page.getByLabel("Describe the situation")).toHaveValue(
    "Water near the landmark",
  );
  await expect(
    page.getByRole("button", { name: "Send report", exact: true }),
  ).toBeDisabled();
  await page
    .getByLabel("Describe the situation")
    .fill("Corrected: knee deep water near Ekta Nagar.");
  await page.getByLabel("I reviewed this transcript").check();
  const submitted = page.waitForRequest(
    (r) =>
      new URL(r.url()).pathname === "/api/reports" && r.method() === "POST",
  );
  await page.getByRole("button", { name: "Send report", exact: true }).click();
  expect((await submitted).postDataJSON()).toMatchObject({
    text: "Corrected: knee deep water near Ekta Nagar.",
    channel: "voice",
    language: "en",
    consent: true,
  });
  await expect(page.getByText("Your voice has been received")).toBeVisible();
  expect(previews).toBe(1);
});
test("voice provider errors stay visible; replacement audio clears review", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/transcriptions", async (route) => {
    calls++;
    await route.fulfill({
      status: calls === 1 ? 503 : 200,
      contentType: "application/json",
      body: JSON.stringify(
        calls === 1
          ? { detail: "Transcription is not configured" }
          : { text: "Original transcript", language: "en" },
      ),
    });
  });
  await page.goto("/");
  await page.getByLabel("अहवालाची भाषा").selectOption("en");
  await page
    .locator("input[type=file]")
    .setInputFiles({
      name: "first.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("fixture"),
    });
  await page.getByLabel("I agree to share").check();
  await page.getByRole("button", { name: "Transcribe and review" }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Transcription is not configured",
  );
  await page.getByRole("button", { name: "Transcribe and review" }).click();
  await page.getByLabel("I reviewed this transcript").check();
  await page
    .locator("input[type=file]")
    .setInputFiles({
      name: "second.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("replacement"),
    });
  await expect(page.getByLabel("Describe the situation")).toHaveValue("");
  await expect(page.getByLabel("I reviewed this transcript")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Send report", exact: true }),
  ).toBeDisabled();
});
