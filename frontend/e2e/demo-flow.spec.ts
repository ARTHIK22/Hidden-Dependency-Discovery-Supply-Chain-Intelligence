import { expect, test } from "@playwright/test";

test("authenticated demo workflow works across the main product areas", async ({ page }) => {
  test.setTimeout(180_000);
  const runMarker = process.env.HDI_E2E_RUN_MARKER ?? `local-${Date.now()}`;
  const email = `qa-${runMarker}@example.test`;
  const password = "Demo-Only-Password-42";
  const goal = `Find hidden lithium dependencies behind Acme Electronics. E2E run ${runMarker}.`;
  const pageErrors: string[] = [];
  const apiErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 500) {
      apiErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("link", { name: "Create an account" }).click();
  await page.getByLabel("Full name").fill("Demo QA User");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL("http://localhost:5175/");
  await expect(page.getByRole("status")).toContainText("Demo mode");

  await page.goto("/investigations");
  await expect(page.getByRole("heading", { name: "Investigation History" })).toBeVisible();
  await expect(page.getByText("DEMO — Illustrative electronics supply chain")).toBeVisible();

  await page.goto("/graph");
  await expect(page.getByRole("heading", { name: "Dependency Graph" })).toBeVisible();
  await expect(page.getByText("Supplier B", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Relationship verification statuses")).toContainText("Conflicted / rejected");
  await page.locator(".react-flow__node").filter({ hasText: "Supplier B" }).click({ force: true });
  await expect(page.getByText("Entity identity could not be confidently resolved.")).toBeVisible();
  await page.getByRole("button", { name: "Close entity details" }).click();
  await page.locator(".react-flow__edge-path").last().click({ force: true });
  await expect(page.getByText("Verification status")).toBeVisible();
  await expect(page.locator(".graph-evidence-item").first()).toBeVisible();

  await page.goto("/entities");
  await expect(page.getByRole("heading", { name: "Entity Explorer" })).toBeVisible();
  await expect(page.getByText("Acme Electronics", { exact: true })).toBeVisible();
  await page.locator(".entity-item").filter({ hasText: "Acme Electronics" }).click();
  await expect(page.getByText("Identity resolution has not run; this entity’s canonical identity is unconfirmed.")).toBeVisible();

  await page.goto("/evidence");
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await expect(page.getByText("DEMO fixture — no external source verified").first()).toBeVisible();
  await expect(page.locator(".evidence-confidence").filter({ hasText: "35%" }).first()).toBeVisible();
  await page.locator(".evidence-row").first().click();
  await expect(page.getByText("RELATIONSHIP VERIFICATION")).toBeVisible();

  await page.goto("/risks");
  await expect(page.getByRole("heading", { name: "Risk Intelligence" })).toBeVisible();
  await expect(page.getByText("72", { exact: true }).first()).toBeVisible();

  await page.goto("/alerts");
  await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
  await expect(page.getByText("DEMO: Illustrative supplier concentration")).toBeVisible();
  await page.getByRole("button", { name: "Mark all read" }).click();
  await expect(page.locator(".alerts-counter")).toContainText("0 Unread");

  await page.goto("/watchlist");
  await expect(page.getByRole("heading", { name: "Watchlist" })).toBeVisible();
  await expect(page.getByText("Supplier B", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Add to Watchlist" }).click();
  await page.locator(".watch-candidates").getByRole("button", { name: /Manufacturer B/ }).click();
  const added = page.locator(".watch-card").filter({ hasText: "Manufacturer B" });
  await expect(added).toBeVisible();
  await added.getByRole("button", { name: "Remove Manufacturer B" }).click();
  await expect(added).toHaveCount(0);

  await page.getByRole("button", { name: "Search anything" }).click();
  await page.getByLabel("Search investigations, entities, evidence, and risks").fill("Supplier B");
  await expect(page.getByRole("button", { name: /Open Supplier B/ })).toBeVisible();
  await page.getByRole("button", { name: "Close search" }).click();

  await page.goto("/investigations/new");
  await page.locator("textarea.investigation-textarea").fill(goal);
  await page.getByRole("button", { name: "Save Investigation" }).click();
  await expect(page).toHaveURL(/\/investigations\/[0-9a-f-]+$/i);
  const investigationId = new URL(page.url()).pathname.split("/").at(-1)!;
  await expect(page.getByRole("heading", { name: "Structured plan" })).toBeVisible();
  await page.getByRole("button", { name: "Start Research" }).click();
  await expect(page.getByText("Demo research mode — external source discovery is not configured. This run does not generate fictional source records or findings.")).toBeVisible();
  await expect(page.locator(".research-message")).toContainText("No source records or findings were generated.");
  await expect(page.locator(".research-counts")).toContainText("Sources discovered");
  await expect(page.locator(".research-counts")).toContainText("Evidence collected");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Research completed" })).toBeVisible();
  await expect(page.getByText("Demo research mode — external source discovery is not configured. This run does not generate fictional source records or findings.")).toBeVisible();
  await page.getByRole("button", { name: "Start Verification" }).click();
  await expect(page.getByText("Research findings have been resolved and verified against available evidence. Risk analysis has not started.")).toBeVisible();
  await expect(page.getByText("Verification completed; risk analysis is pending.")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Research findings have been resolved and verified against available evidence. Risk analysis has not started.")).toBeVisible();

  await page.goto("/risks");
  await page.getByLabel("Investigation for risk analysis").selectOption(investigationId);
  await page.getByRole("button", { name: "Analyze Risk" }).click();
  await expect(page.locator(".risk-analysis-controls")).toContainText("RISK_ANALYZED");
  await expect(page.locator(".risk-table")).toContainText("No source-backed risk scores were available; unknown factors remain in the saved snapshot.");

  const token = await page.evaluate(() => window.localStorage.getItem("hdi.access_token"));
  expect(token).toBeTruthy();
  const fixtureHeaders = { Authorization: `Bearer ${token}` };
  await page.request.post(`http://localhost:8001/api/e2e/monitoring/${investigationId}/seed-anchor`, { headers: fixtureHeaders }).then(async (response) => {
    expect(response.ok()).toBeTruthy();
  });
  await page.goto(`/investigations/${investigationId}`);
  await expect(page.getByRole("region", { name: "Continuous monitoring" })).toBeVisible();
  await page.getByLabel("Monitoring interval").selectOption("15");
  await page.getByRole("button", { name: "Enable Monitoring" }).click();
  await expect(page.locator(".monitoring-state-pill")).toContainText("MONITORING ENABLED");
  const fixtureChange = await page.request.post(`http://localhost:8001/api/e2e/monitoring/${investigationId}/seed-change`, { headers: fixtureHeaders });
  expect(fixtureChange.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Run Now" }).click();
  await expect(page.locator(".monitoring-state-pill")).toContainText("MONITORING COMPLETED", { timeout: 30_000 });
  await expect(page.locator(".monitoring-list-block").first()).toContainText("NEW UPSTREAM DEPENDENCY");
  await expect(page.locator(".monitoring-list-block").nth(1)).toContainText("RESEARCH ENTITY");
  await expect(page.getByRole("button", { name: "Open follow-up investigation" }).first()).toBeVisible();
  await expect(page.locator(".monitoring-timeline")).toContainText("followup completed");
  await expect(page.locator(".monitoring-timeline")).toContainText("monitoring completed");

  await page.goto("/watchlist");
  await page.getByRole("button", { name: "Add to Watchlist" }).click();
  await page.getByRole("group", { name: "Watch target type" }).getByRole("button", { name: "Risk Condition" }).click();
  await page.getByLabel("Risk threshold").fill("65");
  await page.locator(".watch-candidates button").first().click();
  const conditionWatch = page.locator(".watch-card").filter({ hasText: "threshold 65/100" });
  await expect(conditionWatch).toBeVisible();
  await conditionWatch.getByRole("button", { name: /Remove/ }).click();
  await expect(conditionWatch).toHaveCount(0);

  await page.goto("/reports");
  await page.getByLabel("Investigation for report").selectOption(investigationId);
  await page.getByRole("button", { name: "Generate report" }).click();
  await expect(page.locator(".report-content")).toContainText("Entities: 2");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^report-.*\.txt$/);
  const jsonDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "JSON", exact: true }).click();
  expect((await jsonDownloadPromise).suggestedFilename()).toMatch(/^report-.*\.json$/);
  const csvDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV", exact: true }).click();
  expect((await csvDownloadPromise).suggestedFilename()).toMatch(/^report-.*\.csv$/);

  await page.getByRole("button", { name: "Notifications" }).click();
  await expect(page.getByText("DEMO: Illustrative material dependency").first()).toBeVisible();

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Demo QA User" })).toBeVisible();
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();

  console.log(`Isolated E2E run marker: ${runMarker}; user: ${email}`);
  await page.getByRole("button", { name: "Open profile menu" }).click();
  await expect(page.getByRole("button", { name: "My Profile" })).toBeVisible();
  await expect(page.getByText("Development Workspace")).toBeVisible();
  await expect(page.getByRole("button", { name: "Settings", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Preferences" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  const loginEmail = page.getByLabel("Email", { exact: true });
  const loginPassword = page.getByLabel("Password", { exact: true });
  expect(await loginEmail.evaluate((input) => (input as HTMLInputElement).validity.valueMissing)).toBe(true);
  expect(await loginPassword.evaluate((input) => (input as HTMLInputElement).validity.valueMissing)).toBe(true);
  await loginEmail.fill("not-an-email");
  expect(await loginEmail.evaluate((input) => (input as HTMLInputElement).validity.typeMismatch)).toBe(true);
  expect(await page.locator(".login-card").evaluate((form) => !(form as HTMLFormElement).checkValidity())).toBe(true);

  await loginEmail.fill(email);
  await loginPassword.fill("Wrong-Demo-Password-42");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText("Incorrect email or password.");

  await page.getByRole("button", { name: "Show password" }).click();
  await expect(loginPassword).toHaveAttribute("type", "text");
  await expect(page.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Hide password" }).click();
  await expect(loginPassword).toHaveAttribute("type", "password");
  await expect(page.locator(".login-google")).toHaveCount(0);
  await expect(page.locator(".login-divider")).toHaveCount(0);
  await expect(page.locator(".login-card")).not.toContainText("Google sign-in is not configured");
  await page.getByRole("button", { name: "Forgot password?" }).click();
  await expect(page.getByRole("status")).toContainText("For password reset help, contact your workspace administrator.");
  await expect(page.locator(".login-card")).not.toContainText("not configured");

  await loginEmail.focus();
  await page.keyboard.press("Tab");
  await expect(loginPassword).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Show password" })).toBeFocused();

  await loginPassword.fill(password);
  await page.route("**/auth/login", async (route) => route.abort());
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText("Unable to connect. Please check your connection and try again.");
  await page.unroute("**/auth/login");

  for (const viewport of [
    { width: 1280, height: 800 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    const authLayout = await page.evaluate(() => {
      const screen = document.querySelector<HTMLElement>(".auth-login-screen")!;
      const composition = document.querySelector<HTMLElement>(".auth-composition")!;
      const card = document.querySelector<HTMLElement>(".login-card")!;
      const ambience = document.querySelector<HTMLElement>(".auth-ambience")!;
      const screenRect = screen.getBoundingClientRect();
      const cardRect = card.getBoundingClientRect();
      return {
        documentOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        cardInsideScreen: cardRect.left >= screenRect.left && cardRect.right <= screenRect.right,
        cardFitsItsContent: card.scrollWidth <= card.clientWidth + 1,
        ambienceBehindForm: Number(getComputedStyle(ambience).zIndex) < Number(getComputedStyle(composition).zIndex),
        networkHiddenOnMobile: window.innerWidth > 640 || getComputedStyle(document.querySelector(".auth-network")!).display === "none",
      };
    });
    expect(authLayout.documentOverflow, `login page overflow at ${viewport.width}px`).toBe(false);
    expect(authLayout.cardInsideScreen, `login card exceeds the screen at ${viewport.width}px`).toBe(true);
    expect(authLayout.cardFitsItsContent, `login card content overflows at ${viewport.width}px`).toBe(true);
    expect(authLayout.ambienceBehindForm).toBe(true);
    expect(authLayout.networkHiddenOnMobile).toBe(true);
  }

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/login");
  await page.getByRole("link", { name: /Create an account/ }).click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.route("**/auth/login", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.continue();
  });
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Signing in..." })).toBeDisabled();
  await expect(page).toHaveURL("http://localhost:5175/");
  await page.unroute("**/auth/login");

  for (const viewport of [
    { width: 1920, height: 1080 },
    { width: 1440, height: 900 },
    { width: 1366, height: 768 },
    { width: 1280, height: 800 },
    { width: 1024, height: 768 },
    { width: 900, height: 800 },
    { width: 768, height: 1024 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Investigate hidden dependencies." })).toBeVisible();
    const dashboardOverflowsHorizontally = await page.evaluate(() => {
      const shell = document.querySelector<HTMLElement>(".app-shell");
      return document.documentElement.scrollWidth > window.innerWidth + 1 || (shell?.scrollWidth ?? 0) > window.innerWidth + 1;
    });
    expect(dashboardOverflowsHorizontally, `dashboard overflow at ${viewport.width}px`).toBe(false);

    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Reports", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Open Report" }).first().click();
    await expect(page.locator(".report-document")).toBeVisible();
    await expect(page.getByRole("button", { name: "Open profile menu" })).toBeVisible();
    const reportLayout = await page.evaluate(() => {
      const bounds = (selector: string) => {
        const element = document.querySelector<HTMLElement>(selector);
        if (!element) return null;
        const rect = element.getBoundingClientRect();
        return { right: rect.right, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
      };
      return {
        documentOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        appShellOverflow: (document.querySelector<HTMLElement>(".app-shell")?.scrollWidth ?? 0) > window.innerWidth + 1,
        hero: bounds(".report-hero"),
        controls: bounds(".report-controls"),
        title: bounds(".report-heading h1"),
        profile: bounds(".profile-trigger"),
        profileDetails: (() => {
          const trigger = document.querySelector<HTMLButtonElement>(".profile-trigger");
          const avatar = trigger?.querySelector<HTMLElement>(".profile-trigger-avatar");
          const userInfo = trigger?.querySelector<HTMLElement>(".profile-user-info");
          const chevron = trigger?.querySelector<HTMLElement>(".profile-chevron");
          const notification = document.querySelector<HTMLElement>(".notification-trigger");
          if (!trigger || !avatar || !userInfo || !chevron || !notification) return null;
          const triggerRect = trigger.getBoundingClientRect();
          const avatarRect = avatar.getBoundingClientRect();
          const chevronRect = chevron.getBoundingClientRect();
          const notificationRect = notification.getBoundingClientRect();
          const avatarStyle = getComputedStyle(avatar);
          return {
            avatarIsInsideTrigger: trigger.contains(avatar),
            avatarIsWithinTrigger: avatarRect.left >= triggerRect.left && avatarRect.right <= triggerRect.right && avatarRect.top >= triggerRect.top && avatarRect.bottom <= triggerRect.bottom,
            avatarPosition: avatarStyle.position,
            avatarMarginTop: avatarStyle.marginTop,
            chevronIsVisible: chevron.getClientRects().length > 0,
            chevronIsWithinTrigger: chevronRect.left >= triggerRect.left && chevronRect.right <= triggerRect.right && chevronRect.top >= triggerRect.top && chevronRect.bottom <= triggerRect.bottom,
            userInfoVisible: getComputedStyle(userInfo).display !== "none",
            centerDifference: Math.abs((triggerRect.top + triggerRect.bottom) / 2 - (notificationRect.top + notificationRect.bottom) / 2),
          };
        })(),
      };
    });
    expect(reportLayout.documentOverflow, `reports overflow at ${viewport.width}px`).toBe(false);
    expect(reportLayout.appShellOverflow, `reports app shell overflows at ${viewport.width}px`).toBe(false);
    expect(reportLayout.hero).not.toBeNull();
    expect(reportLayout.controls).not.toBeNull();
    expect(reportLayout.title).not.toBeNull();
    expect(reportLayout.profile).not.toBeNull();
    expect(reportLayout.profileDetails).not.toBeNull();
    expect(reportLayout.profileDetails!.avatarIsInsideTrigger).toBe(true);
    expect(reportLayout.profileDetails!.avatarIsWithinTrigger).toBe(true);
    expect(reportLayout.profileDetails!.avatarPosition).toBe("static");
    expect(reportLayout.profileDetails!.avatarMarginTop).toBe("0px");
    expect(reportLayout.profileDetails!.chevronIsVisible).toBe(true);
    expect(reportLayout.profileDetails!.chevronIsWithinTrigger).toBe(true);
    expect(reportLayout.profileDetails!.userInfoVisible).toBe(viewport.width > 900);
    expect(reportLayout.profileDetails!.centerDifference).toBeLessThanOrEqual(1);
    expect(reportLayout.controls!.scrollWidth, `report controls overflow at ${viewport.width}px`).toBeLessThanOrEqual(reportLayout.controls!.clientWidth + 1);
    expect(reportLayout.title!.scrollWidth, `report title overflows at ${viewport.width}px`).toBeLessThanOrEqual(reportLayout.title!.clientWidth + 1);
    expect(reportLayout.controls!.right, `report controls exceed hero at ${viewport.width}px`).toBeLessThanOrEqual(reportLayout.hero!.right + 1);
    expect(reportLayout.profile!.right, `profile exceeds viewport at ${viewport.width}px`).toBeLessThanOrEqual(viewport.width + 1);

    if (viewport.width === 768 || viewport.width === 390) {
      await page.getByRole("button", { name: "Open profile menu" }).click();
      await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
      await page.locator(".profile-menu").evaluate(async (menu) => {
        await Promise.all(menu.getAnimations().map((animation) => animation.finished));
      });
      const dropdownBounds = await page.evaluate(() => {
        const profile = document.querySelector<HTMLElement>(".profile-trigger")!.getBoundingClientRect();
        const menu = document.querySelector<HTMLElement>(".profile-menu")!.getBoundingClientRect();
        return { profileBottom: profile.bottom, left: menu.left, right: menu.right, top: menu.top };
      });
      expect(dropdownBounds.top).toBeGreaterThanOrEqual(dropdownBounds.profileBottom + 7);
      expect(dropdownBounds.left).toBeGreaterThanOrEqual(0);
      expect(dropdownBounds.right).toBeLessThanOrEqual(viewport.width + 1);
      await page.getByRole("button", { name: "Open profile menu" }).click();
    }

    await page.goto("/risks");
    await expect(page.getByRole("heading", { name: "Risk Intelligence" })).toBeVisible();
    const riskLayout = await page.evaluate(() => {
      const shell = document.querySelector<HTMLElement>(".app-shell");
      const page = document.querySelector<HTMLElement>(".risk-page");
      const selector = document.querySelector<HTMLElement>(".risk-analysis-controls select");
      const table = document.querySelector<HTMLElement>(".risk-table");
      return {
        documentOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        shellOverflow: (shell?.scrollWidth ?? 0) > window.innerWidth + 1,
        pageOverflow: page ? page.scrollWidth > page.clientWidth + 1 : true,
        selectorFits: selector ? selector.getBoundingClientRect().right <= window.innerWidth + 1 : false,
        tableOverflow: table ? table.scrollWidth > table.clientWidth + 1 : false,
      };
    });
    expect(riskLayout.documentOverflow, `risk document overflow at ${viewport.width}px`).toBe(false);
    expect(riskLayout.shellOverflow, `risk app shell overflow at ${viewport.width}px`).toBe(false);
    expect(riskLayout.pageOverflow, `risk page overflow at ${viewport.width}px`).toBe(false);
    expect(riskLayout.selectorFits, `risk selector exceeds the viewport at ${viewport.width}px`).toBe(true);
    if (viewport.width >= 1280) expect(riskLayout.tableOverflow, `risk table overflows internally at ${viewport.width}px`).toBe(false);

    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    const settingsLayout = await page.evaluate(() => {
      const shell = document.querySelector<HTMLElement>(".app-shell");
      const page = document.querySelector<HTMLElement>(".settings-page");
      const cards = [...document.querySelectorAll<HTMLElement>(".setting-card")];
      return {
        documentOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        shellOverflow: (shell?.scrollWidth ?? 0) > window.innerWidth + 1,
        pageOverflow: page ? page.scrollWidth > page.clientWidth + 1 : true,
        cardsFit: cards.every((card) => card.getBoundingClientRect().right <= window.innerWidth + 1 && card.scrollWidth <= card.clientWidth + 1),
      };
    });
    expect(settingsLayout.documentOverflow, `settings document overflow at ${viewport.width}px`).toBe(false);
    expect(settingsLayout.shellOverflow, `settings app shell overflow at ${viewport.width}px`).toBe(false);
    expect(settingsLayout.pageOverflow, `settings page overflow at ${viewport.width}px`).toBe(false);
    expect(settingsLayout.cardsFit, `settings card content overflows at ${viewport.width}px`).toBe(true);
  }

  expect(apiErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
});
