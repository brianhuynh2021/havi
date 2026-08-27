import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const FIXED_NOW_ISO = "2026-08-11T03:00:00.000Z";
const APP_ORIGIN = new URL(
  process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100",
).origin;
const API_PATH_PREFIXES = [
  "/analytics",
  "/auth",
  "/billing",
  "/brand-profile",
  "/calendar",
  "/connections",
  "/content",
  "/inbox",
  "/queue",
  "/workspaces",
];

const authTokens = {
  accessToken: "visual-access-token",
  refreshToken: "visual-refresh-token",
  activeWorkspaceId: "w1",
  needsOnboarding: false,
};

const workspace = {
  id: "w1",
  name: "Spa An Nhiên",
  industry: "spa",
  plan: "trial",
  publish_mode: "review_first",
  created_at: "2026-08-10T00:00:00Z",
};

const connection = {
  workspace_id: "w1",
  platform: "facebook",
  account_name: "Spa An Nhiên",
  status: "connected",
  failure_reason: null,
  expires_at: null,
  connected_at: "2026-08-10T00:00:00Z",
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    headers: {
      "Access-Control-Allow-Origin": APP_ORIGIN,
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Headers": "authorization,content-type",
      "Access-Control-Allow-Methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS",
    },
    body: JSON.stringify(body),
  });
}

function emptyWeek() {
  return [
    { date: "2026-08-10", items: [] },
    {
      date: "2026-08-11",
      items: [
        {
          id: "c1",
          workspace_id: "w1",
          job_id: "j1",
          channel: "facebook_page",
          kind: "Bài ảnh",
          text: "Ưu đãi gội đầu thảo dược cuối tuần",
          status: "scheduled",
          scheduled_at: "2026-08-11T02:30:00Z",
          version_no: 1,
        },
      ],
    },
    { date: "2026-08-12", items: [] },
    { date: "2026-08-13", items: [] },
    { date: "2026-08-14", items: [] },
    { date: "2026-08-15", items: [] },
    { date: "2026-08-16", items: [] },
  ];
}

async function mockApi(page: Page) {
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (!API_PATH_PREFIXES.some((prefix) => path.startsWith(prefix))) {
      return route.continue();
    }

    if (request.method() === "OPTIONS") {
      return route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": APP_ORIGIN,
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Headers": "authorization,content-type",
          "Access-Control-Allow-Methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS",
        },
      });
    }

    if (path === "/auth/me") {
      return json(route, {
        id: "u1",
        email: "huong@spaannhien.vn",
        name: "Chị Hương",
        active_workspace_id: "w1",
        needs_onboarding: false,
      });
    }
    if (path === "/auth/refresh") {
      return json(route, {
        access_token: authTokens.accessToken,
        refresh_token: authTokens.refreshToken,
        active_workspace_id: authTokens.activeWorkspaceId,
        needs_onboarding: authTokens.needsOnboarding,
      });
    }
    if (path === "/workspaces") return json(route, [workspace]);
    if (path === "/workspaces/w1") return json(route, workspace);
    if (path.endsWith("/video/posts")) {
      return json(route, { items: [], total: 0, limit: 20, offset: 0 });
    }
    if (path.endsWith("/trends/hot")) return json(route, []);
    if (path === "/connections") return json(route, [connection]);
    if (path === "/queue/brief") {
      return json(route, {
        generated_at: FIXED_NOW_ISO,
        window_hours: 24,
        activity: { published: 1, inbox_received: 2, replies_sent: 1, publish_failed: 0 },
        attention_total: 2,
        attention_costly: 1,
        calendar_gaps: [{ date: "2026-08-13", weekday: "Thứ Năm" }],
        silent_channels: [],
        time_saved_minutes: 5,
        time_saved_actions: [
          { action: "Trả lời khách", count: 1, minutes_each: 2, minutes_total: 2 },
          { action: "Đăng bài lên kênh", count: 1, minutes_each: 3, minutes_total: 3 },
        ],
      });
    }
    if (path === "/queue") {
      return json(route, {
        items: [
          {
            kind: "inbox",
            id: "i1",
            title: "Khách hỏi giá",
            detail: "Combo gội đầu bao nhiêu tiền ạ?",
            channel: "facebook",
            category: "price",
            priority: 10,
            waiting_since: FIXED_NOW_ISO,
            assigned_to_user_id: null,
            assigned_to_name: null,
            platform_url: null,
            href: "/app/inbox",
          },
        ],
        total: 1,
      });
    }
    if (path === "/billing/subscription") {
      return json(route, {
        workspace_id: "w1",
        plan: "trial",
        status: "trialing",
        current_period_end: "2026-08-18T00:00:00Z",
        token_quota_used: 12000,
        token_quota_limit: 400000,
        seats_used: 1,
        seats_limit: 2,
        channels_used: 1,
        channels_limit: 2,
        billing_cycle: "monthly",
        extra_seats: 0,
        extra_channels: 0,
        posts_remaining_estimate: 25,
        tokens_per_post: 15000,
        tokens_per_post_measured: false,
        days_until_due: 7,
      });
    }
    if (path === "/billing/invoices") return json(route, []);
    if (path === "/brand-profile") {
      return json(route, {
        workspace_id: "w1",
        industry: "spa",
        tone: "thân thiện, gần gũi, gọi khách là chị em",
        banned_claims: ["cam kết 100%"],
        faq: [],
        logo_url: null,
        brand_colors: [],
      });
    }
    if (path === "/analytics/dashboard") {
      return json(route, {
        drafts: 1,
        pending_approval: 3,
        scheduled: 2,
        published: 5,
        failed: 1,
      });
    }
    if (path === "/analytics/events") {
      return json(route, {
        items: [
          {
            id: "e1",
            workspace_id: "w1",
            job_id: "j1",
            request_id: null,
            job_kind: "content.approve",
            input_summary: "approved_by=user@example.com",
            output_summary: null,
            tokens_in: 0,
            tokens_out: 0,
            provider: null,
            duration_ms: 120,
            error: null,
            created_at: FIXED_NOW_ISO,
          },
          {
            id: "e2",
            workspace_id: "w1",
            job_id: "j2",
            request_id: null,
            job_kind: "publish.run_job",
            input_summary: null,
            output_summary: null,
            tokens_in: 0,
            tokens_out: 0,
            provider: "facebook",
            duration_ms: 310,
            error: "Graph API token expired",
            created_at: "2026-08-10T09:00:00Z",
          },
        ],
        total: 2,
        limit: 5,
        offset: 0,
      });
    }
    if (path === "/analytics/summary") {
      return json(route, {
        published_posts: 5,
        inbox_items: 1,
        replies_sent: 0,
        failed_posts: 0,
        change_vs_previous_period: {},
      });
    }
    if (path === "/analytics/timeseries") {
      return json(route, {
        metric: "published_posts",
        points: [
          { period: "2026-W29", value: 0 },
          { period: "2026-W30", value: 2 },
          { period: "2026-W31", value: 1 },
          { period: "2026-W32", value: 2 },
        ],
      });
    }
    if (path === "/analytics/attribution") {
      return json(route, [
        {
          channel: "facebook_page",
          posts: 5,
          share: 1,
          note: "Tạm tính theo bài đã đăng; chưa có engagement snapshot.",
        },
      ]);
    }
    if (path === "/analytics/operations") {
      return json(route, {
        window_start: "2026-08-05T17:00:00Z",
        window_end: "2026-08-12T17:00:00Z",
        event_count: 12,
        error_count: 3,
        error_rate: 0.25,
        avg_duration_ms: 120,
        p95_duration_ms: 410,
        content_generation_count: 4,
        slow_content_generation_count: 1,
        content_generation_p95_ms: 21_000,
        slow_content_generation_threshold_ms: 20_000,
        tokens_in: 1000,
        tokens_out: 250,
        tokens_total: 1250,
        job_count: 4,
        avg_tokens_per_job: 312,
        est_cost_per_job_vnd: 900,
        generated_draft_count: 20,
        approved_draft_count: 2,
        draft_usage_rate: 0.1,
        est_cost_per_approved_draft_vnd: 9000,
        pricing_as_of: "2026-08-26",
        pricing_is_stale: false,
        providers: [
          { provider: "openai", event_count: 8, error_count: 1, tokens_total: 900 },
          { provider: "facebook", event_count: 4, error_count: 2, tokens_total: 0 },
        ],
        publish: {
          total: 5,
          succeeded: 4,
          dead_letter: 1,
          success_rate: 0.8,
          dead_letter_rate: 0.2,
        },
      });
    }
    if (path === "/inbox") {
      return json(route, {
        items: [
          {
            id: "i1",
            workspace_id: "w1",
            platform: "facebook",
            type: "message",
            recipient_id: "psid-lan",
            content: "Combo gội đầu bao nhiêu tiền ạ?",
            author_name: "Chị Lan",
            status: "drafted",
            ai_suggested_reply: "Dạ combo gội đầu thảo dược 180k ạ.",
            external_message_id: "m1",
            created_at: FIXED_NOW_ISO,
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      });
    }
    if (path === "/calendar") return json(route, { days: emptyWeek() });
    if (path === "/content/quota") {
      return json(route, {
        used: 12000,
        limit: 100000,
        remaining: 88000,
        near_limit: false,
        exceeded: false,
        resets_at: "2026-09-01T00:00:00Z",
      });
    }
    if (path === "/content/publish-jobs") {
      return json(route, [
        {
          id: "job-1",
          workspace_id: "w1",
          content_item_id: "c1",
          channel: "facebook_page",
          status: "dead_letter",
          scheduled_at: "2026-08-10T13:00:00Z",
          attempt_count: 4,
          next_attempt_at: null,
          failure_kind: "auth_permission",
          failure_detail: "token expired",
          external_post_id: null,
          published_at: null,
        },
      ]);
    }
    if (path === "/content") {
      return json(route, {
        items: [
          {
            id: "c1",
            workspace_id: "w1",
            job_id: "j1",
            channel: "facebook_page",
            kind: "Bài ảnh",
            text: "Nội dung chăm sóc da mùa nắng cho khách quen",
            status: "pending_approval",
            version_no: 1,
          },
          {
            id: "c2",
            workspace_id: "w1",
            job_id: "j1",
            channel: "zalo_oa",
            kind: "Tin nhắn",
            text: "Nhắc lịch ưu đãi gội đầu thảo dược cuối tuần",
            status: "pending_approval",
            version_no: 1,
          },
        ],
        total: 2,
        limit: 50,
        offset: 0,
      });
    }

    return json(route, { detail: "visual route not mocked" }, 404);
  });
}

async function freezeClock(page: Page) {
  await page.addInitScript((fixedNowIso) => {
    const fixedNow = new Date(fixedNowIso as string).valueOf();
    const RealDate = Date;
    class MockDate extends RealDate {
      constructor(...args: (string | number | Date)[]) {
        if (args.length === 0) {
          super(fixedNow);
          return;
        }
        // @ts-expect-error super with spread
        super(...args);
      }
      static now() {
        return fixedNow;
      }
    }
    window.Date = MockDate as DateConstructor;
  }, FIXED_NOW_ISO);
}

async function prepare(page: Page) {
  await freezeClock(page);
  await mockApi(page);
}

type VisualRoute = (typeof publicRoutes)[number] | (typeof authenticatedRoutes)[number];

async function expectReady(page: Page, route: VisualRoute) {
  await expect(page.getByRole("heading", { name: route.heading }).first()).toBeVisible();
  if ("auth" in route && route.auth) {
    await expect(page).not.toHaveURL(/\/login$/);
    if ((page.viewportSize()?.width ?? 9999) <= 768) {
      await expect(
        page.getByRole("navigation", { name: /Điều hướng mobile/i }),
      ).toBeVisible();
    }
  }
  if (route.name === "landing") {
    await expect(page.getByText(/chỉ công bố phản hồi khách hàng hoặc hiệu quả đầu tư/i)).toBeAttached();
    await expect(page.getByText(/Trực Inbox 24\/7/i)).toHaveCount(0);
  }
  if (route.name === "billing") {
    await expect(
      page.getByText(/không bao gồm.*cam kết số bài, lead hay doanh thu/i),
    ).toBeAttached();
    await expect(page.getByText("1 / 2")).toHaveCount(2);
    await expect(page.getByText(/khoảng 25 bài/i)).toBeVisible();
    await expect(page.getByText(/Đã dùng 3% số bài viết/i)).toBeVisible();
    await expect(page.getByText(/Dùng thử trọn vẹn sức mạnh/i)).toHaveCount(0);
  }
  if (route.name === "calendar") {
    await expect(page.getByText(/Duyệt trước/i).first()).toBeVisible();
    await expect(page.getByText(/Giờ Vàng VN/i)).toHaveCount(0);
  }
  if (route.name === "operations") {
    await expect(page.getByText("Tạo bài chậm")).toBeVisible();
    await expect(page.getByText(/NaN/)).toHaveCount(0);
  }
}

// Đường dẫn tiếng Anh chuẩn (Gate J) và tiêu đề đúng như app render. Bảng này
// từng trỏ vào các route tiếng Việt cũ (`/bao-cao`, `/noi-dung`) sau khi app đã
// chuyển sang `/app/...`, nên mọi route có auth đều 404 và cả suite đỏ — một
// suite đỏ toàn bộ thì không ai đọc nữa, và nó thôi bắt được hồi quy thật.
const publicRoutes = [
  {
    name: "landing",
    path: "/",
    heading: /Mọi kênh trong tầm kiểm soát/i,
    auth: false,
  },
  { name: "login", path: "/login", heading: /Đăng nhập Havi/i, auth: false },
] as const;

const authenticatedRoutes = [
  { name: "dashboard", path: "/app", heading: /Việc cần làm/i, auth: true },
  { name: "content", path: "/app/content", heading: /Đăng bài/i, auth: true },
  { name: "calendar", path: "/app/calendar", heading: /Lịch [Đđ]ăng/i, auth: true },
  { name: "reports", path: "/app/reports", heading: /Báo [Cc]áo/i, auth: true },
  { name: "settings", path: "/app/settings", heading: /Cài [Đđ]ặt/i, auth: true },
  { name: "billing", path: "/app/billing", heading: /Gói cước/i, auth: true },
  { name: "inbox", path: "/app/inbox", heading: /Hội thoại/i, auth: true },
  {
    name: "operations",
    path: "/app/internal/operations",
    heading: "Vận hành",
    auth: true,
  },
] as const;

function defineRouteChecks(route: VisualRoute) {
  test(`${route.name} visual baseline`, async ({ page }, testInfo) => {
    await prepare(page);
    await page.goto(route.path);
    await expectReady(page, route);
    await page.waitForLoadState("networkidle");
    await expectReady(page, route);

    await expect(page).toHaveScreenshot(`${route.name}-${testInfo.project.name}.png`);
  });

  test(`${route.name} accessibility smoke`, async ({ page }) => {
    await prepare(page);
    await page.goto(route.path);
    await expectReady(page, route);
    await page.waitForLoadState("networkidle");
    await expectReady(page, route);

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .disableRules(["color-contrast"])
      .analyze();
    expect(result.violations).toEqual([]);
  });
}

test.describe("public routes", () => {
  for (const route of publicRoutes) defineRouteChecks(route);
});

test.describe("authenticated routes", () => {
  // Cần CẢ cookie và localStorage. `src/middleware.ts` chạy ở edge nên chỉ đọc
  // được cookie `havi_session` — localStorage vô hình với nó, và thiếu cookie thì
  // mọi `/app/*` bị redirect về `/login` trước khi React kịp chạy. Còn
  // `havi.tokens` trong localStorage là thứ route guard phía client đọc.
  test.use({
    storageState: {
      cookies: [
        {
          name: "havi_session",
          value: authTokens.accessToken,
          domain: new URL(APP_ORIGIN).hostname,
          path: "/",
          expires: -1,
          httpOnly: false,
          secure: false,
          sameSite: "Lax" as const,
        },
      ],
      origins: [
        {
          origin: APP_ORIGIN,
          localStorage: [
            { name: "havi.tokens", value: JSON.stringify(authTokens) },
          ],
        },
      ],
    },
  });

  for (const route of authenticatedRoutes) defineRouteChecks(route);

  test("inbox mobile thread remains usable without horizontal overflow", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile", "Mobile-only responsive regression");

    await prepare(page);
    await page.goto("/app/inbox");
    const inboxRoute = authenticatedRoutes.find((route) => route.name === "inbox")!;
    await expectReady(page, inboxRoute);
    await page.waitForLoadState("networkidle");

    await expect(page.getByText("Chọn một hội thoại ở danh sách bên trái để bắt đầu")).toBeHidden();

    await page.getByRole("button", { name: /Chị Lan.*Combo gội đầu/i }).click();
    await expect(page.getByRole("button", { name: "Quay lại danh sách hội thoại" })).toBeVisible();
    await expect(page.getByLabel(/Trả lời Chị Lan/i)).toBeVisible();

    const widths = await page.evaluate(() => ({
      content: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(widths.content).toBeLessThanOrEqual(widths.viewport);

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .disableRules(["color-contrast"])
      .analyze();
    expect(result.violations).toEqual([]);
    await expect(page).toHaveScreenshot("inbox-thread-mobile.png");
  });
});
