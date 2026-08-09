# Havi — Product & Engineering Roadmap

> Phiên bản: 2026-08-09
>
> Trạng thái: execution-ready
>
> Nguồn chuẩn: `HANDOFF.md`, 6 prototype trong `prototypes/`,
> `TECHNICAL_SPEC.md`, `SYSTEM_ARCHITECTURE.md` và code hiện tại.

## Quy ước theo dõi

- `[x]`: đã triển khai và có bằng chứng kiểm tra tương ứng.
- `[ ]`: chưa làm xong hoặc chưa qua đủ exit criteria.

Chỉ tích `[x]` sau khi code, test và tài liệu liên quan đều hoàn thành; không tích
chỉ vì đã scaffold hoặc UI đang hiển thị bằng fixture.

## 1. Mục tiêu và nguyên tắc sản phẩm

Havi là nhân viên marketing AI cho hộ kinh doanh và doanh nghiệp nhỏ tại Việt
Nam. MVP phải chứng minh được một vòng giá trị hoàn chỉnh:

```text
Nạp ảnh / ghi âm / vài dòng
            ↓
Havi tạo nhiều bản nội dung theo kênh
            ↓
Chủ doanh nghiệp xem, sửa và duyệt
            ↓
Hệ thống đăng đúng lịch qua API chính thức
            ↓
Havi báo kết quả bằng ngôn ngữ kinh doanh dễ hiểu
```

Các nguyên tắc không được phá trong bất kỳ sprint nào:

1. `review_first` là mặc định; không có nội dung nào lên mạng khi chủ chưa duyệt.
2. Reply khách luôn cần duyệt, trừ từng câu FAQ đã được chủ duyệt sẵn.
3. Không giả danh khách hàng trong seeding hoặc reply.
4. Chỉ tích hợp qua API chính thức; không crawler hoặc automation vi phạm điều khoản.
5. Một content job gọi LLM một lần để sinh nhiều đầu ra theo kênh.
6. Frontend không giữ database credential, OAuth secret, token nền tảng hoặc prompt production.
7. Mọi dữ liệu và job phải được scope theo workspace; không leak chéo tenant.
8. Publish job phải idempotent; retry không được tạo bài đăng trùng.

### Quyết định đã đổi: email là danh tính đăng nhập, không phải SĐT

Bản roadmap đầu chọn SĐT + OTP làm kênh đăng nhập chính. Đã đổi sang **email +
mật khẩu**, vì hai lý do:

1. **Chi phí.** OTP SMS ở Việt Nam tốn tiền thật cho mỗi tin (~300–600đ). Mỗi lần
   đăng nhập và mỗi lần bấm "gửi lại mã" đều ăn vào margin gói 299K/tháng — trái
   với mục tiêu ở §9 là giữ chi phí AI + hạ tầng trong biên gói giá.
2. **Tâm lý người dùng.** Nhiều người Việt e dè đưa số điện thoại vì spam call/tin
   rác, nên bắt buộc SĐT ngay ở bước đăng ký làm giảm tỷ lệ activation.

Không dùng username: thêm một thứ người dùng phải nghĩ ra và dễ quên, trong khi
email họ đã có sẵn và dùng lại được để khôi phục tài khoản.

**SĐT không bị bỏ** — nó thành field tuỳ chọn, thêm trong Cài đặt (`PUT /auth/phone`),
chỉ để nhận bản nháp/nhắc duyệt qua Zalo OA. Nghĩa là Zalo OA (P1) vẫn cần thu số
ở bước đó, chỉ là không chặn đăng ký.

Social login (Google) là hướng mở tiếp theo cho cả hai lý do trên — chưa làm, xem
§4 P1.

**Zalo Login: không làm.** Zalo chỉ là kênh *gửi tin* (Zalo OA — bản nháp, nhắc
duyệt), không phải kênh đăng nhập. Lưu ý dễ nhầm: Zalo OA và Zalo Login là hai
OAuth app khác nhau; tương tự Google Business (đăng bài) khác Google Sign-In
(đăng nhập). Các biến `zalo_client_id`/`google_client_id` trong `core/config.py`
là cho kênh publish, **không** dùng được để đăng nhập.

Vậy danh sách kênh đăng nhập chốt lại: **email + mật khẩu** (đã chạy), **Google
Sign-In** (P1). Không SĐT, không Zalo, không username.

## 2. Cách đọc bộ thiết kế

Bộ prototype thể hiện hai lớp khác nhau và roadmap phải tách chúng rõ ràng:

- **Design-complete:** giao diện và interaction chạy đúng bằng fixture/mock để duyệt UX.
- **Production-ready:** giao diện đã nối API thật, có auth, persistence, error state,
  audit, security và vận hành.

Một màn xuất hiện trong prototype không đồng nghĩa backend của tính năng đó nằm
trong MVP pilot. Những claim chưa có production capability không được đưa lên
landing page public.

### Ma trận thiết kế → release

| Thiết kế | Phạm vi cần tái tạo | Design-complete | Production-ready |
|---|---|---:|---:|
| MVP App — Tổng quan | App Shell 232px, stats, ô nạp liệu, suggestion, Zalo banner, activity feed | Đã code; QA Tuần 1 | Tuần 8 |
| MVP App — Tạo nội dung | Raw inputs, generating states, 5 draft cards, toggle publish mode, bulk/single approval | Tuần 2 | Tuần 6 |
| MVP App — Lịch đăng | Lịch tuần, post theo kênh, dữ liệu đồng bộ từ bài đã duyệt | Tuần 2 | Tuần 6 |
| MVP App — Khách tiềm năng | Lead cards, suggested reply, send-after-approval, FAQ strip | Tuần 2 | Sau pilot; pilot dùng intake thủ công |
| MVP App — Báo cáo | Stats, attribution bars, weekly chart, nhận xét bằng ngôn ngữ đời thường | Tuần 2 | Tuần 8, với dữ liệu MVP tối thiểu |
| Đăng nhập / Đăng ký | Email + mật khẩu, signup, forgot/reset password qua email, success states | Tuần 3 | Tuần 4 |
| Onboarding | Chọn ngành, nối kênh, learning state, first draft | Tuần 3 | Tuần 7 |
| Landing Page | Hero, cách hoạt động, ngành, nguyên tắc, CTA | Đã code (`/gioi-thieu`) | Tuần 12 — cần rà soát claim lần cuối + chốt pricing |
| AI Marketing | Demo 4 trạm theo persona, progress/log/result | Tuần 3 | Internal sales demo; không phải core app |
| Kiến Trúc Hệ Thống | Spec nội bộ cho queue, adapters, quota và event log | Đã có | Được hiện thực dần Tuần 4–9 |

## 3. Baseline hiện tại

### Đã hoàn thành

Frontend:

- [x] Next.js 16 App Router + TypeScript, lint và production build chạy được.
- [x] Design tokens Havi và font Merriweather + Inter.
- [x] App Shell với sidebar 232px và responsive navigation.
- [x] Tab Tổng quan được tách thành feature, dùng fixture riêng và bám prototype.
- [x] Route `/` hiện là static page; chưa có routing cho các màn còn lại.

Backend:

- [x] FastAPI scaffold với 12 domain router và OpenAPI schema.
- [x] Pydantic contracts cho auth, workspace, brand profile, media, content,
  calendar, connections, inbox, leads, analytics và billing.
- [x] Content state machine và event envelope ban đầu.
- [x] Celery worker/Beat — `havi.content.generate_drafts`,
  `havi.scheduler.dispatch_due_posts` và `havi.publish.run_due` đã chạy thật.
  Ba task còn lại trong `beat_schedule` (refresh token, CRM nudge, engagement)
  vẫn là khung `NotImplementedError` cho Tuần 8+.
- [x] 263 backend tests đang pass (contract/state-machine/provider-router +
  auth/workspace/brand-profile/media/content/approval/publish/connections chạy
  thật trên Postgres + MinIO; Graph API dùng `httpx.MockTransport`, không gọi
  mạng thật); Ruff đang pass. 82 web test pass.

Architecture/docs:

- [x] Monorepo boundary, frontend/backend ownership và future split strategy đã chốt.
- [x] Sơ đồ hệ thống, frontend modules và content state machine đã có.
- [x] Handoff ghi đầy đủ fidelity, interaction và approval workflow.

### Chưa hoàn thành

- [ ] Frontend routes, interaction thật và visual regression tests. Auth,
  onboarding, Tạo nội dung và Lịch đăng đã nối API thật; Landing Page,
  Terms/Privacy đã dựng (70 test web pass). Tổng quan, Khách tiềm năng, Báo cáo
  và quên mật khẩu vẫn fixture. Chưa có visual regression.
- [x] Generated TypeScript API client.
- [x] PostgreSQL models/repositories cho auth, workspace/member và brand profile;
  Alembic migrations thật; tenant isolation có test (403 khi JWT hợp lệ nhưng
  không phải thành viên). Repository cho media/content/calendar/connections/
  publish đã có và test tenant isolation thật. **Chưa xong:** inbox/leads.
- [x] JWT access + refresh token xoay vòng, đăng ký/đăng nhập email + mật khẩu
  (Argon2), đặt lại mật khẩu qua mã 6 số. **Chưa xong:** email provider thật
  (dùng `debug_code` khi `HAVI_DEBUG=true`), endpoint logout/revoke session.
- [x] Object storage (MinIO) đã dùng thật: signed upload + magic-byte validation
  ở `/media`. Redis + Celery đã dùng thật: `havi.content.generate_drafts` chạy
  Content Engine trong worker.
- [x] LLM content pipeline (multi-provider, Gemini ưu tiên) + structured output
  validation + ghi token vào `event_log`. **Chưa có:** quota chặn theo workspace,
  và cost tính bằng tiền.
- [x] OAuth/token encryption và adapter publish Facebook — lớp mã hoá token
  (Fernet) + signed OAuth state chống CSRF + bảng `platform_connections` và
  `publish_jobs` với unique constraint chống đăng trùng (migration
  `b7f77094b946`), router `/connections/*`, adapter Graph API v21.0, và Celery
  beat gọi scheduler thật. **Chưa kiểm:** một bài thật lên Page thật (cần
  Facebook app pilot).
- [x] Scheduler/retry/idempotency/dead-letter production behavior — beat mỗi 5
  phút tạo job, worker nhận bằng row lock, retry backoff 60/300/900s cho lỗi tạm
  thời, hai loại lỗi kia đi thẳng dead-letter, và có endpoint thử lại thủ công có
  guard. **Chưa có:** alerting khi số job dead-letter tăng (Tuần 8).
- [ ] CI/CD, staging, observability, alerting và runbook.
- [ ] E2E test cho hành trình signup → draft → approve → publish → report.

Auth, workspace, brand profile, media, content, calendar và connections/publish
đã chạy thật trên Postgres. Các domain còn lại (inbox, leads, analytics, billing)
mới khóa contract và trả `501 Not Implemented`.

### Hạ tầng bắt buộc trước beta

Code hiện tại **chưa đủ để chạy beta thật**. Trước khi chính founder dùng thử,
hệ thống phải có đủ bốn lớp dữ liệu/vận hành sau:

PostgreSQL:

- [x] `users`, `otp_challenges`, `refresh_sessions` (migration `c5a2a7713af1`,
  `eb7685b1cb83` đổi email thành danh tính chính và SĐT thành tuỳ chọn).
- [x] `workspaces`, `workspace_members`, `brand_profiles` — có repository + router
  thật (`/workspaces/*`, `/brand-profile`), test chạy trên Postgres.
- [x] `platform_connections` với token mã hóa (migration `b7f77094b946`,
  unique `(workspace_id, platform)` — nối lại thì cập nhật chứ không tạo bản
  ghi thứ hai).
- [x] `media_assets`, `content_jobs`, `content_items`, `content_item_versions`
  (migration `a974c194ff2c`, `32712ea2080b`).
- [x] `event_log` — insert thật qua `EventLogRepository`. **Chưa có:**
  `engagement_snapshots`. `publish_jobs` đã có với unique constraint trên
  `idempotency_key` — chốt chặn chống đăng trùng ở tầng Postgres.
- [x] Alembic migrations, indexes, foreign keys cho các bảng auth/workspace ở
  trên (`alembic check` sạch). **Chưa xong:** tenant-scoped repository cho các
  domain còn lại, và test tenant isolation.

Redis/job queue:

- [x] Celery broker/result backend — Redis, dùng thật cho content generation và
  publish. Beat có lịch cho cả hai.
- [ ] Rate limit OTP/content generation.
- [x] Job retry, lock ngắn hạn và dead-letter handling — cho publish job:
  `FOR UPDATE SKIP LOCKED`, backoff 60/300/900s, dead-letter sau 4 lần hoặc ngay
  với lỗi không retry được. **Chưa có:** cùng cơ chế cho content job (hiện
  `GenerationFailed` là dừng hẳn, không có dead-letter queue riêng).
- [ ] Cache profile/quota có chiến lược invalidation rõ.

Object storage:

- [x] Signed upload (presigned POST), MIME whitelist + magic-byte check, size
  limit enforce ở tầng storage bằng `content-length-range`, `workspace_id` trong
  object key và mọi query scope theo workspace — `tests/test_media_flow.py`,
  14 case chạy thật trên MinIO.
- [ ] Chính sách lưu, xóa và lifecycle cho ảnh/audio/video.
- [x] Không lưu file upload trực tiếp trong database hoặc filesystem tạm của API
  (client POST thẳng lên object storage, API chỉ giữ metadata + `object_key`).

Vận hành dữ liệu:

- [ ] Backup tự động và restore rehearsal.
- [ ] Migration forward/rollback strategy.
- [ ] Secret management và token encryption key rotation plan.
- [ ] Log/metrics/alerting, nhưng không ghi OTP, token hoặc PII nhạy cảm.
- [ ] Staging tách production; demo data tách dữ liệu thật.

Không được mời khách beta nếu chưa restore được backup, chưa test tenant
isolation hoặc publish retry vẫn có thể đăng trùng.

## 4. Phạm vi release

### P0 — Pilot MVP bắt buộc

- [x] Email + mật khẩu login/signup, refresh token xoay vòng. **Chưa xong:** logout/revoke chủ động.
- [ ] Một workspace/user trong happy path; data model vẫn hỗ trợ multi-workspace.
- [ ] Onboarding ngành đã chạy thật (chọn ngành → tạo workspace → vào app), và
  bước 2 nối Facebook Page đã gọi `/connections` thật.
  **Chưa xong:** màn sửa brand voice cơ bản.
- [x] Upload ảnh + nhập text đã chạy thật end-to-end. Ghi âm để sau (nút disable).
- [x] Một content job sinh nhiều draft theo kênh bằng structured output —
  backend và frontend đều đã nối; job chạy thật cần worker + API key LLM.
- [x] Editor, version history, duyệt lẻ, duyệt hàng loạt và lên lịch — backend
  và frontend đều đã nối API thật.
- [ ] Facebook Page OAuth + publish bằng API chính thức. **Đã có:** OAuth thật,
  adapter Graph API v21.0, scheduler + worker, UI nối/nối lại/ngắt kênh. **Chưa
  có:** một bài thật lên Page thật — cần Facebook app pilot (§12), và đó là thứ
  duy nhất còn thiếu để tick mục này.
- [x] Calendar hiển thị đúng ngày/giờ VN và trạng thái publish đầy đủ.
  **Chưa xong:** `publishing`/`published`/`failed` mới có nhãn, chưa có bài thật
  ở trạng thái đó vì chưa đăng thử lên Page thật.
- [ ] Dashboard tối thiểu: draft, scheduled, published, failed và engagement snapshot nếu API cho phép.
- [ ] Audit/event log, token usage, quota, retry và idempotency.
- [ ] Responsive web cho desktop, tablet và mobile phổ biến.

### P1 — Chỉ làm khi P0 đã qua release gate

- [ ] Google Business adapter.
- [ ] Zalo OA notification/approval.
- [ ] Media library đầy đủ và audio transcription.
- [ ] Unified inbox từ các API chính thức.
- [ ] Lead pipeline đơn giản và attribution khách đến từ đâu.
- [ ] Brand profile nâng cao: banned claims, FAQ editor, logo và brand colors.
- [ ] Workspace members/roles UI đầy đủ.
- [ ] Đăng nhập bằng Google (OAuth) — bỏ luôn bước nhập mật khẩu, cost gần 0.
  `users.password_hash` đã nullable sẵn cho hướng này.
- [ ] Billing bằng một cổng thanh toán Việt Nam.

### P2 — Sau khi có dữ liệu pilot

- [ ] TikTok/YouTube adapters.
- [ ] Video pipeline dựng Reel/TikTok thật (Video Understanding → Transcript →
  Edit Engine → EditPlan.json → Renderer) — thiết kế đã ghi ở
  `docs/architecture/SYSTEM_ARCHITECTURE.md` §5.3, chưa code.
- [ ] CRM lifecycle automation 14/30 ngày.
- [ ] A/B testing tiêu đề/giờ đăng.
- [ ] Full-auto unlock theo lịch sử duyệt và tỷ lệ sửa.
- [ ] Social listening tự động, chỉ khi có API/nguồn dữ liệu hợp lệ.
- [ ] Native mobile app.

### Không làm trong pilot

- [ ] Crawler group hoặc scraping không được nền tảng cho phép.
- [ ] Reply AI tự gửi ngoài FAQ đã duyệt sẵn.
- [ ] Nhiều payment gateway cùng lúc.
- [ ] Real-time analytics phức tạp.
- [ ] Machine learning tối ưu giờ đăng khi chưa đủ dữ liệu.

### Việt Nam-first

Phiên bản đầu phục vụ người Việt tại Việt Nam, không lấy flow SaaS quốc tế rồi
dịch chữ lại. Mọi quyết định sản phẩm phải ưu tiên bối cảnh sử dụng thực tế:

- [ ] Tiếng Việt là ngôn ngữ mặc định; copy ngắn, đời thường, tránh jargon marketing/AI.
- [ ] Hỗ trợ nhập số `0xxxxxxxxx`, normalize và lưu dạng `+84`; hiển thị lại theo format quen thuộc.
- [ ] Email provider để gửi mã đặt lại mật khẩu (hiện trả `debug_code` khi `HAVI_DEBUG=true`).
- [ ] SĐT tuỳ chọn trong Cài đặt cho Zalo OA — không dùng để đăng nhập (xem §1).
- [ ] Múi giờ mặc định `Asia/Ho_Chi_Minh`; ngày theo `dd/MM/yyyy`, giờ 24h, tiền tệ VND.
- [ ] Thiết kế mobile-first cho Android phổ biến, màn hình 360px và mạng 4G không ổn định.
- [ ] Upload phải resume/retry hợp lý, nén ảnh phía client khi phù hợp và không bắt user chờ vô nghĩa.
- [ ] Facebook Page là kênh publish P0; Zalo OA là ưu tiên P1 sau khi xác nhận quyền/API thực tế.
- [ ] Onboarding bắt đầu bằng một ngành cụ thể và ví dụ Việt Nam thật, đề xuất Spa/Tiệm nhỏ.
- [ ] Brand voice hiểu cách xưng hô `chị/em`, `anh/em`, tên tiệm và vùng miền; user luôn sửa được.
- [ ] Banned claims theo ngành phải chặn các câu cam kết quá mức, đặc biệt làm đẹp, tài chính và bất động sản.
- [ ] Consent, quyền xóa dữ liệu, opt-out và chính sách lưu dữ liệu phải phù hợp
  quy định Việt Nam hiện hành. **Đã có:** trang Privacy nêu đủ quyền chủ thể dữ
  liệu và thời hạn xoá 30 ngày; màn đăng ký có link consent thật. **Chưa có:**
  endpoint xoá tài khoản và xuất dữ liệu (hiện xử lý thủ công qua email), và
  chưa qua thẩm định pháp lý.
- [ ] Support beta dùng kênh quen thuộc với cohort, ưu tiên Zalo/điện thoại thay vì chỉ email ticket.
- [ ] Pricing hiển thị bằng VND và chỉ public sau khi đo được chi phí AI/hạ tầng trên khách Việt thật.

## 5. Kế hoạch thực thi 12 tuần

Ước lượng cho 1 frontend, 1 backend và product/design/QA bán thời gian. Nếu chỉ
có một full-stack developer, dùng cùng dependency order nhưng dự kiến 16–22 tuần.

### Tuần 1 — Khóa nền tảng frontend và contract

Mục tiêu: app có route structure ổn định, API contract dùng được và mọi thay đổi
sau đó đi qua cùng một quality gate.

Frontend:

- [x] Chốt route groups: `(app)`, `(auth)`, `(onboarding)`, `(public)`.
- [x] Chuyển App Shell thành layout dùng chung cho 5 tab (`app/(app)/layout.tsx`).
- [x] Tạo primitives tối thiểu: Button, Card, Badge, Input/Textarea, OtpInput,
  Empty/Error/Loading state (`components/ui/`).
- [x] Chốt tokens cho color, typography, spacing, radius, shadow, focus và disabled.
- [x] Tạo fixture convention theo feature; không để fixture trong route.
- [x] Thêm test setup cho component (Vitest + React Testing Library).
  **Chưa xong:** integration test và automated accessibility check.

Backend/platform:

- [ ] Khóa dependency rules frontend/backend bằng architecture tests hoặc lint rules.
- [ ] Tạo module template gồm public interface, service, ports/adapters và tests.
- [ ] Quy định ADR ngắn cho mọi ngoại lệ boundary hoặc công nghệ hạ tầng mới.
- [ ] Freeze OpenAPI naming, error envelope, pagination và auth headers.
- [x] Sinh TypeScript client trực tiếp trong frontend (`npm run generate:api` →
  `apps/web/src/lib/api-client/schema.d.ts`), không tạo package riêng vì chỉ có
  một consumer.
- [x] Tạo Docker Compose cho PostgreSQL, Redis và MinIO (`docker-compose.yml` ở root).
- [x] Khởi tạo Alembic và migration smoke test (`alembic check` + round-trip up/down
  verify trên Postgres thật).
- [ ] Thêm request ID/job ID vào log context.

QA/product:

- [ ] Lập checklist pixel fidelity cho 6 prototype ở desktop và mobile.
- [ ] Lập inventory copy/claim; đánh dấu claim chỉ dành cho demo.
- [ ] Chốt ngành pilot đầu tiên, mặc định đề xuất Spa.

Exit criteria:

- [x] Web lint/build/test pass.
- [x] Backend lint/test/migration check pass (59 test, ruff, `alembic check`).
- [x] OpenAPI client generate repeatably và compile trong frontend.
- [x] Local stack khởi động bằng tài liệu duy nhất (`README.md` → `npm run infra:up`).

### Tuần 2 — Design-complete MVP App

Mục tiêu: toàn bộ 5 tab app chính chạy bằng fixture và đúng interaction prototype.

Frontend:

- [x] Hoàn thiện navigation route-aware và active state (`usePathname` + `aria-current`).
- [x] Dựng tab Tạo nội dung: raw input list, drop zone, generating progress, draft cards.
- [x] Dựng toggle `review_first/full_auto`; mặc định `review_first`, chọn `full_auto`
  hiện cảnh báo là đang khoá trong pilot.
- [x] Dựng single approve, bulk approve và pill state. **Lưu ý:** chưa phải
  *optimistic* thật — chưa có API nên chưa có rollback khi backend từ chối.
- [x] Dựng Lịch đăng với fixture bám `content_item.scheduled_at`. **Chưa xong:**
  đồng bộ động từ draft vừa duyệt (fixture hai tab hiện độc lập).
- [x] Dựng Khách tiềm năng với reply approval, sent state và FAQ strip.
- [x] Dựng Báo cáo với stats, attribution bars, chart (CSS thuần) và Havi insight.
- [ ] Thêm keyboard/focus states; không chỉ test bằng mouse.

Backend:

- [ ] Xác nhận API hiện tại đủ cho mọi UI state.
- [ ] Bổ sung schema còn thiếu trước khi frontend bắt đầu nối API.
- [ ] Viết contract tests cho approve-all, reject, reschedule và publish failure types.

QA/product:

- [ ] Đối chiếu từng tab với `Havi - MVP App.dc.html`.
- [ ] Chụp baseline desktop/mobile để dùng cho visual regression.
- [ ] Kiểm tra copy minh bạch danh tính trong lead reply.

Exit criteria:

- [x] 5 tab điều hướng được không reload toàn trang (`next/link` client-side).
- [x] Generating, pending, scheduled, sent và error fixture states đều xem được.
- [x] Không có action gửi/publish giả lập nào bỏ qua approval rule.

### Tuần 3 — Design-complete acquisition, auth và onboarding

Mục tiêu: hoàn thành toàn bộ bề mặt thiết kế trước khi nối business backend.

Frontend:

- [x] Landing Page responsive (`/gioi-thieu`), anchor navigation và CTA dẫn tới
  `/dang-ky`. **Cố ý khác prototype:** claim đã viết lại theo capability thật —
  bỏ "tự động đăng 4 kênh" (publish là Tuần 7), bỏ săn khách hội nhóm/CRM/làm
  đẹp ảnh (P2), bỏ Maps/LinkedIn/YouTube khỏi danh sách kênh. **Chưa có bảng
  giá:** §12 chốt chỉ public sau khi đo cost trên khách Việt thật, nên thay bằng
  lời mời beta. `landing-screen.test.tsx` có test chặn regression claim.
- [x] Auth flows: email login, signup (tên + email + mật khẩu), forgot/reset
  password qua mã 6 số trong email, resend countdown và success routes.
- [x] Onboarding 3 bước: industry, connections, learning state và first draft.
- [ ] AI Marketing demo theo persona cho sales/internal review.
- [x] Thêm reduced-motion behavior cho progress animation
  (`@media (prefers-reduced-motion: reduce)` ở mọi spinner).
- [x] Route guards cho guest, needs onboarding và authenticated — làm thẳng bản
  thật ở Tuần 4 thay vì bản mock, xem `lib/auth/route-guard.tsx`.

Product/legal:

- [ ] Rà soát landing claims: số kênh, tự động đăng, social listening, giá và trial.
- [ ] Ẩn hoặc đổi copy với capability chưa production-ready.
- [x] Terms (`/dieu-khoan`) và Privacy (`/bao-mat`) đã dựng, link từ footer
  landing và màn đăng ký. Nội dung bám đúng dữ liệu hệ thống thật xử lý (email,
  mật khẩu Argon2id, ảnh trên object storage, event_log không chứa nội dung
  bài), nói rõ liệu thô được gửi cho Gemini/Anthropic/OpenAI, và nêu đủ quyền
  chủ thể dữ liệu theo luật VN. `legal-page.test.tsx` (13 test) chặn regression
  claim hai chiều. **Chưa xong:** cần luật sư rà trước khi mời khách beta —
  đây là bản nháp kỹ thuật, không phải văn bản đã thẩm định.

QA:

- [ ] Form validation, keyboard flow cho ô mã 6 số (backspace, paste) và resend.
- [ ] Responsive check tối thiểu 360px, 768px, 1280px và 1440px.
- [ ] Accessibility check cho label, contrast, focus order và disabled states.

Exit criteria:

- [ ] Tất cả prototype có route/code-native implementation để review.
- [ ] Không còn link giữa các file `.dc.html` trong product app.
- [ ] Design review sign-off cho desktop và mobile.

### Tuần 4 — Persistence, auth, workspace và brand profile

Mục tiêu: người dùng thật có thể đăng ký, tạo workspace và hoàn thành onboarding.

Backend:

- [x] Models/migrations cho user, OTP challenge, refresh session, workspace,
  workspace member, brand profile và audit event (`domain/models/`, migration
  `c5a2a7713af1` + `eb7685b1cb83`, verify bằng `alembic check` + round-trip
  up/down + insert/query thật trên Postgres).
- [x] Password hashing bằng Argon2id (`core/security.py`). Không dùng passlib
  (module `crypt` bị xoá ở Python 3.13+) và không dùng bcrypt (truncate âm thầm ở
  72 bytes — mật khẩu tiếng Việt có dấu ăn ~3 bytes/ký tự nên chạm giới hạn chỉ
  sau ~24 ký tự).
- [x] Email chuẩn hoá lowercase để không tạo 2 tài khoản từ `A@x.vn` và `a@x.vn`.
  Mã đặt lại mật khẩu có TTL, attempt limit và resend cooldown — test thật ở
  `tests/test_auth_flow.py`. **Chưa xong:** email provider thật (đang trả
  `debug_code` khi `HAVI_DEBUG=true` — xem §12 "Quyết định cần chốt").
- [x] SĐT tuỳ chọn (`PUT /auth/phone`) cho Zalo OA, chuẩn hoá về `+84…`, unique
  để một số không gắn 2 tài khoản. Không dùng để đăng nhập.
- [x] JWT access token + rotated refresh token (`/auth/sign-up`, `/auth/login/email`,
  `/auth/password-reset/*`, `/auth/refresh`, `/auth/me` đều chạy thật trên Postgres).
  **Chưa xong:** endpoint logout/revoke session theo yêu cầu (refresh token chỉ
  bị revoke khi xoay vòng qua `/auth/refresh`, chưa có cách revoke chủ động).
- [x] Không tiết lộ email nào đã đăng ký: sai mật khẩu và email không tồn tại trả
  cùng 401 + cùng message; `/auth/password-reset/request` luôn trả 202.
- [x] Tenant-scoped repository/dependency; deny-by-default khi thiếu workspace.
  `PathWorkspaceMemberDep` (api/deps.py) chặn 403 mọi route `{workspace_id}` nếu
  JWT hợp lệ nhưng không phải thành viên — test thật `test_khong_the_doc_workspace_cua_nguoi_khac`.
  `WorkspaceDep` (workspace đọc từ JWT) đã dùng thật ở `/brand-profile`, verify
  bằng `test_hai_workspace_khong_doc_thay_profile_cua_nhau` + 409 khi chưa onboarding.
  Media, content và calendar cũng đã verify tenant isolation thật (không đọc/duyệt/
  đổi lịch được bài của workspace khác dù biết UUID). **Chưa xong:** connections/
  inbox/leads vẫn `501`.
- [x] Workspace create/activate và onboarding completion state. `/workspaces`
  (CRUD), `/workspaces/{id}/activate` (đổi JWT), `/workspaces/{id}/members`
  (invite/list/remove, chặn xoá owner cuối) — `tests/test_workspace_flow.py`,
  9 case chạy thật trên Postgres.
- [x] Brand profile thật: `GET/PUT /brand-profile` (tone, banned_claims, faq,
  logo_url, brand_colors), tạo lazy theo `industry` của workspace ở lần gọi đầu
  — `tests/test_brand_profile_flow.py`, 7 case chạy thật. **Chưa xong:** chưa có
  cache profile cho worker (worker sẽ đọc trực tiếp DB), và PUT hành xử như PATCH
  nên không xoá được `logo_url` về null.
- [x] Encrypt sensitive fields bằng application key management — token nền tảng
  mã hoá bằng Fernet (`core/token_crypto.py`), khoá đọc từ
  `HAVI_TOKEN_ENCRYPTION_KEY`. Thiếu khoá thì ném lỗi chứ không lưu plaintext.
  14 test gồm: bản mã không chứa token gốc, mã hoá hai lần ra hai bản khác
  nhau, sai khoá/bản mã bị sửa đều bị từ chối.

Frontend:

- [x] Nối auth API, session bootstrap, refresh và logout. Đăng nhập/đăng ký gọi
  API thật; `apiClient` tự refresh khi gặp 401 và gộp nhiều 401 song song thành
  một lượt refresh (refresh token xoay vòng — gọi hai lần bằng token cũ sẽ bị
  revoke cả session). Token nằm trong `lib/auth/token-store.ts`, là nơi duy nhất
  đọc/ghi, để đổi sang httpOnly cookie sau chỉ phải sửa một file.
- [x] Route guards thật cho guest/onboarding/app (`lib/auth/route-guard.tsx`,
  6 test). Là guard UX — dữ liệu thật vẫn do backend chặn bằng JWT + tenant scope.
- [x] Nối industry onboarding: bước 1 gọi `POST /workspaces` rồi
  `POST /workspaces/{id}/activate` để lấy token mới — phải hai lượt vì JWT sau
  đăng ký được ký trước khi có workspace, thiếu bước activate thì route guard đá
  ngược về `/onboarding` thành vòng lặp kín. Tên tiệm điền sẵn từ `/auth/me`.
  `tests/onboarding-screen.test.tsx` 5 case; verify thật trên Postgres:
  `/brand-profile` trả 409 với token sau signup và 200 với token sau activate.
  Bước 2 (nối Facebook Page) đã bỏ fixture, gọi `/connections` thật (Tuần 7).
  **Chưa xong:** màn sửa brand voice/tone.
- [x] Xử lý loading, sai mật khẩu và network failure ở màn đăng nhập/đăng ký
  (nút disable khi đang gửi, lỗi hiện qua `role="alert"`, mất mạng có copy tiếng
  Việt riêng). **Chưa xong:** mã hết hạn và throttled ở màn quên mật khẩu.
- [ ] Thêm screen chọn workspace khi user có nhiều workspace.

Tests/security:

- [ ] Integration test chứng minh workspace A không đọc/sửa workspace B.
- [x] Tests cho brute force mã đặt lại mật khẩu, refresh token rotation + chặn tái
  sử dụng. **Chưa xong:** logout revoke (chưa có endpoint).
- [x] Không log OTP, JWT, refresh token hoặc PII nhạy cảm (chỉ lưu hash trong DB).

Exit criteria:

- [x] Signup (email) → onboarding → app chạy end-to-end với DB thật (verify tay
  trên Postgres: `/brand-profile` 409 với token sau signup, 200 với token sau
  activate, `industry` mang đúng ngành đã chọn). **Chưa có** E2E tự động —
  bằng chứng hiện là test frontend + verify tay, xem Tuần 9.
- [ ] Tenant isolation tests bắt buộc pass trong CI.
- [ ] Restart API không làm mất user/workspace/session hợp lệ.

### Tuần 5 — Media ingest và Content Engine

Mục tiêu: người dùng nạp dữ liệu và nhận draft thật từ async job.

Backend/worker:

- [x] Models/migrations cho media asset, content job, content item, content item
  version và event log (migration `32712ea2080b`).
- [x] Signed upload URL (presigned POST); validate MIME (whitelist + magic bytes),
  size (`content-length-range` ở storage), ownership (`workspace_id` trong object
  key + query scope) và upload completion (`POST /media/{id}/complete` kiểm object
  có thật trên storage trước khi chuyển `pending → raw`).
- [x] Queue content job với idempotency key (header `Idempotency-Key`, unique
  constraint `(workspace_id, idempotency_key)` — bấm hai lần không tốn hai lần
  tiền LLM). **Chưa có:** workspace quota check.
- [x] Content Engine đọc brand profile, gọi LLM một lần và trả structured
  multi-channel output (3 kênh pilot: Facebook Page, Zalo OA, Google Business).
  Multi-provider: Gemini ưu tiên, fallback Anthropic/OpenAI
  (`domain/policies/provider_router.py`). **Chưa có:** chưa gửi bytes ảnh cho
  model — vision là P1/P2, hiện chỉ đưa tên file vào prompt.
- [x] Schema validation (Pydantic + JSON Schema gửi cho provider), banned-claim
  validation (so khớp bỏ dấu + lowercase nên "Cam Kết 100%" cũng bị bắt), và
  fallback sang provider khác khi output lỗi — không retry cùng provider với cùng
  prompt vì gần như ra cùng kết quả.
- [x] Ghi token input/output (cộng cả lần thử thất bại — provider lỗi vẫn tốn
  token), provider phục vụ, latency và job_id vào bảng `event_log` thật.
  **Chưa có:** estimated cost bằng tiền (cần bảng giá theo provider).
- [x] Transient failure → thử provider kế tiếp; mọi provider fail thì job sang
  `failed` với `failure_reason` kèm chi tiết từng lần thử (429/timeout/schema…),
  không chỉ mã lỗi chung. Celery không retry `GenerationFailed` — router đã thử
  hết provider nên retry cùng prompt chỉ tốn thêm tiền.

Frontend:

- [x] Upload ảnh thật: xin ticket → POST thẳng lên object storage → `/complete`.
  Bytes không đi qua API. **Chưa xong:** progress %, cancel giữa chừng và
  preview ảnh (hiện chỉ hiện tên file trong chip).
- [x] Tạo content job từ ảnh/text và poll job status (`use-job-polling.ts`).
  `Idempotency-Key` gắn theo bộ liệu thô — bấm hai lần không tốn hai lần tiền
  LLM, verify thật: cùng key trả về cùng `job.id`.
- [x] Mapping queued/processing/drafts_ready/failed vào UI: spinner khi
  queued/processing, nạp lại hàng chờ khi `drafts_ready`, `failed` hiện lỗi kèm
  nút thử lại. Poll giãn dần 1.5→5s, trần ~3 phút rồi báo thay vì quay vô tận.
- [x] Không dùng timer 2.9s giả lập — fixture draft/generating đã xoá, màn đọc
  `GET /content?status=pending_approval` thật.

Tests:

- [ ] Worker unit tests bằng fake model/provider.
- [ ] Idempotency test: submit/retry không sinh hai content job logic.
- [ ] Contract test cho malformed structured output.

Exit criteria:

- [ ] Upload → content job → nhiều draft chạy thật trên staging.
- [ ] Job lỗi có thể retry và truy vết bằng một correlation ID.
- [ ] Token/cost hiển thị được trong internal event log.

### Tuần 6 — Editor, approval và calendar

Mục tiêu: khóa vòng human-approval-first bằng backend state machine.

Backend:

- [x] Content item update tạo version mới, không overwrite lịch sử — `PATCH
  /content/{id}` và `GET /content/{id}/versions`; chỉ tăng `version_no` khi text
  thật sự đổi.
- [x] Enforce state transitions trong service/domain layer (`ApprovalService` gọi
  `core.content_state.assert_transition`; router chỉ dịch lỗi thành 409).
- [x] Single approve, reject, bulk approve và reschedule transactionally.
  `SELECT ... FOR UPDATE` chặn duyệt hai lần ghi đè `approved_by`.
- [x] Ghi `approved_by`, `approved_at` và audit event (`content.approve` /
  `content.reject` / `content.reschedule` vào `event_log`).
- [x] Calendar là projection từ `content_item.scheduled_at`, gom theo ngày
  `Asia/Ho_Chi_Minh` (bài 6h sáng VN không rơi sang ô hôm trước).
- [x] Không cho reschedule item đã `published` (409), và không cho sửa text bài
  đang `publishing`/`published`.

Frontend:

- [x] Nối draft editor, version history, approve/reject và bulk approve. Editor
  sửa text → `PATCH /content/{id}` tạo version mới; nút Lưu khoá khi chưa sửa gì
  nên không tạo version rác. "Lịch sử" đọc `GET /content/{id}/versions`. Bulk
  approve báo rõ bài nào chưa duyệt được kèm lý do, không im lặng.
- [ ] Optimistic UI có rollback + toast khi backend từ chối. Hiện đang làm ngược
  lại: chờ backend trả lời rồi mới bỏ bài khỏi hàng chờ, 409 thì hiện lỗi và nạp
  lại danh sách. An toàn hơn nhưng chậm hơn một nhịp trên 4G — đổi sang
  optimistic khi có toast component.
- [x] Nối calendar và timezone Asia/Ho_Chi_Minh: lưới tuần đọc `GET /calendar`,
  chuyển tuần trước/sau/tuần này. Ngày gửi lên tính bằng `Intl` theo giờ VN chứ
  không `toISOString()` — hàm đó đổi sang UTC trước nên 6h sáng thứ Ba VN thành
  23h thứ Hai UTC và cả tuần lệch một ngày. Giờ hiển thị cũng ép về VN để máy
  đặt lệch múi giờ vẫn thấy đúng. Verify thật: duyệt bài lúc 20:00 VN → rơi
  đúng ô hôm nay, giờ hiện 20:00. **Chưa xong:** reschedule mới có ở tầng API
  (`rescheduleItem`), UI chưa có kéo-thả hay nút đổi giờ.
- [x] Hiển thị rõ pending, approved, scheduled, publishing, published và failed
  — `statusLabel`/`statusTone` bao đủ 8 giá trị `ContentStatus`, thiếu một cái
  là chủ tiệm phải đọc enum thô.
- [ ] `full_auto` chỉ hiện như controlled setting; chưa mở cho pilot user nếu policy chưa chốt.

Tests:

- [x] State-transition matrix tests (`tests/test_content_state.py` +
  `tests/test_approval_flow.py`, 23 case chạy thật trên Postgres).
- [x] Concurrent approve/bulk approve tests — duyệt hai lần trả 409, một item
  hỏng không làm fail cả lô. **Chưa xong:** test hai session Postgres song song
  thật (fixture hiện dùng chung một transaction nên chỉ verify được logic khoá,
  chưa verify được `FOR UPDATE` chặn race thật).
- [x] Timezone-safe serialization tests: cột `scheduled_at`/`approved_at`/
  `published_at` đổi sang `timestamptz` (migration `6cb25077be10`) — cột naive
  nuốt offset, 20h VN thành 20h UTC. Việt Nam không có DST nên không test DST.

Exit criteria:

- [x] Không có API path đưa item chưa duyệt sang publish trong `review_first` —
  approve là đường duy nhất ra khỏi `pending_approval`, và nó ghi `approved_by`.
- [x] Version history và audit đủ để trả lời ai sửa/duyệt, lúc nào.
- [x] Draft đã duyệt xuất hiện đúng ngày/giờ trên calendar.

### Tuần 7 — Facebook connection và publishing

Mục tiêu: đăng một bài đã duyệt lên Facebook Page đúng lịch và không trùng.

Backend/platform:

- [x] Facebook OAuth start/callback với signed state và CSRF protection —
  `adapters/oauth/facebook.py` (3 bước Graph: code → user token ngắn hạn →
  **user token dài hạn** → Page token qua `/me/accounts`). Bỏ bước đổi dài hạn
  thì Page token cũng ngắn hạn theo và kênh chết sau vài giờ.
  `/start` trả JSON cho frontend; `/callback` trả **302** về app (Facebook điều
  hướng trình duyệt tới, không phải fetch) và `include_in_schema=False` để không
  lọt vào TS client. `code`/`state` khai optional vì bấm "Huỷ" ở Facebook gọi
  lại callback với `error=access_denied` mà không có `code` — khai bắt buộc thì
  chủ tiệm rơi vào 422.
- [x] Lưu token mã hóa; không trả token về frontend. `to_schema` liệt kê field
  bằng tay thay vì `model_validate` — thêm field mới phải sửa có chủ đích, không
  vô tình đẩy token ra response.
- [x] Connection status: connected, expired, revoked; reconnect flow. Nối lại
  cập nhật bản ghi cũ (unique `(workspace_id, platform)`) và xoá `failure_reason`.
  Ngắt kênh xoá hẳn bản ghi kèm token.
- [x] Facebook adapter (`adapters/publishers/facebook.py`) — Graph API v21.0,
  /feed cho bài chữ, /photos cho bài một ảnh, và bài nhiều ảnh upload từng ảnh
  `published=false` lấy `media_fbid` rồi ghép qua `attached_media` (ảnh chưa
  publish không hiện lên Trang nên bước cuối hỏng cũng không lọt gì ra ngoài).
  Map lỗi Graph sang 3 loại. Ưu tiên `code` của Graph hơn HTTP status vì Graph
  trả 400 cho cả token hết hạn lẫn nội dung bị từ chối.
  Graph trả 2xx mà thiếu ID bài → `VALIDATION_PERMANENT` chứ không retry: bài
  rất có thể ĐÃ lên Trang, retry là đường thẳng tới đăng trùng.
- [x] `HAVI_USE_FAKE_PUBLISHER` + validator chặn ở staging/production (cùng khuôn
  `HAVI_USE_MOCK_LLM`). Fake publisher lọt lên staging thì mọi bài báo "đã đăng",
  dashboard xanh, mà Trang trống trơn — sai kiểu im lặng, phải chặn ở deploy.
  **Beta test được mà chưa cần App Review:** Development mode cho người có vai
  trò Tester nối Page của chính họ và đăng thật — đủ cho closed beta 5-10 tiệm,
  thêm thủ công từng người. App Review + Business Verification (cần pháp nhân)
  chỉ bắt buộc khi mở public signup.
- [x] Scheduler tạo publish job đến hạn (`PublishService.dispatch_due`) — quét
  bài `scheduled` tới giờ, idempotent nên beat chạy mỗi 5 phút không sinh job
  trùng. Đã nối vào Celery beat thật: `havi.scheduler.dispatch_due_posts` (mỗi 5
  phút) chỉ *tạo* job rồi `delay()` sang `havi.publish.run_due`, không tự gọi
  Graph API — một Page rate-limit giữ beat hàng chục giây thì mọi workspace khác
  trễ theo. `havi.publish.run_due` có lịch riêng mỗi phút làm lưới an toàn cho
  job đang chờ backoff 60s.
- [x] Repository publish với unique idempotency key, row lock (`FOR UPDATE SKIP
  LOCKED`) và retry backoff 60s/300s/900s. Khoá dựng từ (content_item_id,
  channel, scheduled_at) chuẩn hoá UTC — cùng mốc thời gian viết ở hai offset
  ra cùng khoá, nếu không reschedule về đúng giờ cũ lại đăng trùng.
  `PublishService.run_due`/`run_job` đã ghép adapter + repository và chạy
  đầu-cuối với `FakePublisher`. `worker/publish_service_factory.py` đã lắp sẵn
  service với adapter thật/fake theo config, và `havi.publish.run_due` gọi đúng
  factory này. Task cố ý **không** nhận `content_item_id`: job được nhận bằng
  `claim_due` (row lock ở Postgres) chứ không bằng tham số của message — Celery
  được phép giao lại một message, nên id trong message là đường tới đăng trùng.
  `max_retries=0` (mặc định Celery là 3) để chỉ có một cơ chế retry:
  `mark_failed` xếp lịch theo `PublishFailureKind`.
- [x] Phân loại temporary / auth-permission / validation-permanent
  (`domain/ports/publisher.py`). Chỉ `temporary` được retry — hai loại kia đi
  thẳng dead-letter vì retry cũng hỏng y hệt.
- [x] Dead-letter state + `reset_for_manual_retry` (đặt lại attempt_count vì
  người đã sửa nguyên nhân). Endpoint có guard đã xong:
  `POST /content/publish-jobs/{job_id}/retry` chỉ nhận job đang `dead_letter` —
  `pending` trả 409 vì scheduler sẽ tự chạy (bấm thêm là hai lượt song song),
  `succeeded` trả 409 vì bài đã lên Trang (chạy lại là đăng trùng). Chạy đồng bộ
  và trả kết quả thật thay vì 202: người vừa bấm nút cần biết lần này được hay
  không. `GET /content/publish-jobs?status=dead_letter` là danh sách cần xử lý;
  response không bao giờ chứa `idempotency_key`.

Frontend:

- [x] Connection UI trong onboarding/settings — `features/connections/`
  (`ConnectionList` + `ConnectionCard`) dùng chung cho onboarding bước 2 và tab
  Cài đặt mới (`/cai-dat`). Bước 2 đã bỏ fixture, gọi `GET /connections` thật.
  **Cố ý thêm ngoài prototype:** prototype có 5 tab, đây là tab thứ 6 — token
  Facebook hết hạn sau onboarding thì phải có chỗ thường trực để nối lại, không
  thì lịch đăng chết mà chủ tiệm không có đường sửa.
  Nguồn sự thật là `GET /connections`, không phải state React: quay về từ
  Facebook là một page load mới nên mọi `useState` trước đó đã mất. Onboarding
  đọc `?ket_noi` để resume ở bước 2 — không thì chủ tiệm rơi về bước 1 và bấm
  "Tiếp tục" là tạo tiệm thứ hai trùng tên.
- [ ] Scheduled/publishing/published/failed states và hướng xử lý theo error class.
  **Đã có:** nhãn đủ 8 `ContentStatus` trên Lịch đăng (Tuần 6) và API
  `/content/publish-jobs` để đọc `failure_kind`. **Chưa có:** UI đọc API đó —
  nút "Thử lại" cho bài dead-letter chưa có trên màn nào.
- [x] Reconnect CTA khi token hết hạn hoặc mất quyền — `expired` và `revoked`
  đều hiện nút "Nối lại", nhưng nói lý do khác nhau: hết hạn là chuyện bình
  thường theo thời gian, còn mất quyền thường do ai đó đổi vai trò trên Page nên
  chủ tiệm cần kiểm lại quyền quản trị. Kênh hết hạn **không** tính là "đã nối".
- [x] Không hiển thị TikTok/Zalo/Maps là “đã nối” nếu chỉ là fixture — chip kênh
  trong sidebar trước đây là mảng hằng `["Facebook", "TikTok", "Zalo", "Maps"]`,
  tức mọi chủ tiệm đều thấy bốn kênh "đã nối" dù chưa nối gì và ba trong bốn kênh
  đó còn chưa có adapter. Nay `WorkspaceChannels` đọc `GET /connections` và chỉ
  hiện kênh `connected`. Tên tiệm cũng thôi hardcode "Spa An Nhiên"
  (`WorkspaceName` đọc `GET /workspaces`). `PILOT_PLATFORMS` chỉ có Facebook, có
  test chặn regression nếu ai thêm kênh chưa có adapter.

Tests:

- [x] Adapter tests với `FakePublisher` — làm được toàn bộ phần khó (idempotency,
  row lock, retry, dead-letter) trước khi có quyền Facebook thật.
  **Chưa xong:** recorded/sandbox response từ Graph API thật.
- [x] Double-click và duplicate worker không đăng hai bài — 22 test chạy thật
  trên Postgres, gồm test xác nhận đúng `uq_publish_jobs_idempotency_key` chặn
  chứ không phải FK chặn nhầm.
- [x] Token redaction tests trong logs/errors (`TestTokenRedaction`). Không rơi
  về `response.text` khi thiếu `error.message`, không nội suy `httpx` exception
  (message của nó mang cả URL), và `OAuthAccount.__repr__` che token — vì
  `logger.exception` in cả local variable của frame.
- [x] OAuth/CSRF tests (`test_connection_flow.py`, 39 test): state giả mạo, state
  ký bằng khoá khác, state của Facebook dùng lại ở callback Zalo, và người đã bị
  gỡ khỏi workspace trong 10 phút state còn sống. Graph API thay bằng
  `httpx.MockTransport` nên adapter chạy nguyên vẹn, chỉ tầng socket là giả.
- [x] Router tests (`test_connection_router.py`, 12 test): callback redirect chứ
  không trả JSON, bấm "Huỷ" không rơi vào 422, cross-tenant không thấy kết nối
  của nhau, response không bao giờ chứa token, 501 (chưa có adapter) khác 503
  (thiếu env).
- [x] Retry thủ công qua HTTP (`test_publish_router.py`, 13 test): job của tiệm
  khác trả 404 chứ không 403 (403 xác nhận UUID đó tồn tại), `pending` và
  `succeeded` đều bị chặn 409 và adapter **không** được gọi, retry vẫn hỏng thì
  về lại dead-letter kèm lý do mới, và `/content/publish-jobs` không lọt route
  vào `/content/{content_id}`.
- [x] Beat schedule ↔ task registry (`test_scheduler_wiring.py`, 8 test): mọi
  task name trong `beat_schedule` phải tồn tại thật. Gõ sai một tên thì beat vẫn
  khởi động, vẫn log "sending due task", worker âm thầm bỏ message — lịch đăng
  chết hoàn toàn mà không có một dòng lỗi nào để lần ra.
- [x] Frontend connections (`connections-screen.test.tsx`, 12 test):
  `expired`/`revoked` ra hai câu khác nhau, 501 báo "chưa hỗ trợ" chứ không im
  lặng, API trả về thứ không phải mảng thì báo lỗi chứ không đổ trang, và test
  chặn regression nếu ai liệt kê TikTok/Zalo/Maps vào danh sách kênh.

Exit criteria:

- [ ] Bài đã duyệt được đăng đúng lịch lên Facebook Page pilot. **Chưa làm:** cần
  Facebook app thật + Page pilot (xem §12) — toàn bộ đường đi đã chạy đầu-cuối
  với `FakePublisher`, phần chưa kiểm là Graph API thật.
- [x] Retry không tạo duplicate post — unique constraint ở Postgres + `FOR UPDATE
  SKIP LOCKED`, task không nhận `content_item_id` qua message, và retry thủ công
  chỉ nhận `dead_letter`. 50 test (29 publish flow + 13 router + 8 wiring).
- [x] Auth failure dẫn người dùng về reconnect, không retry vô hạn —
  `AUTH_PERMISSION` đi thẳng dead-letter (không retry) và đánh dấu luôn
  `platform_connections` thành `expired`, nên UI hiện CTA "Nối lại" thay vì chấm
  xanh trong lúc mọi bài đang hỏng.

### Tuần 8 — Dashboard thật, observability và UX lỗi

Mục tiêu: thay fixture Tổng quan/Báo cáo bằng dữ liệu thật và vận hành có thể debug.

Backend:

- [ ] Dashboard summary cho draft/pending/scheduled/published/failed.
- [ ] Engagement snapshot tối thiểu nếu quyền Facebook cho phép.
- [ ] Event log query nội bộ theo workspace/job/request.
- [ ] Monthly token quota và threshold alerts.
- [ ] Rate limiting cho auth, upload và content generation.

Frontend:

- [ ] Nối Tổng quan và Báo cáo vào API.
- [ ] Empty state cho workspace mới; không render số liệu giả.
- [ ] Failed/reconnect/quota-exceeded states có next action rõ.
- [ ] Activity feed lấy từ audit/event projection phù hợp cho người dùng.

Platform:

- [ ] Structured logging, error monitoring, metrics và alerts.
- [ ] Dashboard nội bộ: job latency, failure rate, publish success, token cost.

Exit criteria:

- [ ] Có thể truy một hành động từ web → API → queue → worker → adapter.
- [ ] Dashboard không lẫn fixture khi chạy production mode.
- [ ] Quota chặn job mới có thông báo rõ, không âm thầm vượt chi phí.

### Tuần 9 — Staging hardening và founder release candidate

Mục tiêu: hoàn thành một release candidate đủ an toàn để chính founder dùng thật.

Engineering:

- [ ] E2E: signup → onboarding → connect → upload → generate → edit → approve → publish → report.
- [ ] E2E failure paths: OTP expired, upload fail, LLM fail, OAuth revoke, publish fail.
- [ ] Backup/restore rehearsal và migration rollback/forward strategy.
- [ ] Security review auth, tenant scope, upload, OAuth, secrets và logs.
- [ ] Performance budget cho web; load test API/job queue ở quy mô pilot.
- [ ] Seed/demo workspace tách khỏi dữ liệu pilot.

Product/QA:

- [ ] UAT với 3–5 kịch bản thực tế của ngành pilot.
- [ ] Rà soát copy lần cuối; không hứa feature P1/P2.
- [ ] Viết onboarding/support script và cách báo lỗi cho khách.
- [ ] Triage và đóng toàn bộ P0/P1 defects.

Exit criteria:

- [ ] Không còn lỗi P0/P1 mở.
- [ ] Backup restore thành công trên staging.
- [ ] Security checklist và release checklist được sign-off.
- [ ] Publish success staging đạt ít nhất 95% trong test window, không duplicate.

### Tuần 10 — Founder dogfooding / internal beta

Mục tiêu: chính founder dùng Havi cho một workspace và một Facebook Page thật
trước khi cho bất kỳ khách hàng nào truy cập.

Daily use:

- [ ] Tự signup bằng số điện thoại Việt Nam và hoàn thành onboarding từ đầu.
- [ ] Kết nối Page thật, upload ảnh/text thật và tạo nội dung mỗi ngày.
- [ ] Sửa, duyệt, lên lịch và theo dõi bài đăng thật.
- [ ] Cố tình test mạng chậm, reload, token hết hạn, upload lỗi và publish retry.
- [ ] Ghi lại mọi điểm phải hỏi kỹ thuật hoặc không hiểu copy.
- [ ] Đo thời gian thao tác, token cost, publish latency và số lần phải can thiệp thủ công.

Exit criteria:

- [ ] Dùng liên tục ít nhất 7 ngày với dữ liệu thật.
- [ ] Hoàn thành tối thiểu 10 content jobs và 5 publish jobs thật.
- [ ] Không duplicate publish, không mất dữ liệu, không leak secret/PII.
- [ ] Mọi failed job có reason và cách recovery rõ.
- [ ] Founder có thể tự dùng core flow mà không mở source code hoặc database.

### Tuần 11 — Sửa sau dogfooding và customer beta gate

Mục tiêu: xử lý toàn bộ vấn đề tìm thấy khi founder dùng thật và chuẩn bị vận
hành với người dùng không biết hệ thống bên trong.

Engineering/product:

- [ ] Đóng mọi lỗi severity P0/P1 từ internal beta.
- [ ] Sửa copy/flow khiến founder phải đoán hoặc cần can thiệp kỹ thuật.
- [ ] Chạy lại backup/restore, tenant isolation, OAuth reconnect và duplicate tests.
- [ ] Tạo admin/support view tối thiểu để tra job theo user/workspace mà không đọc DB trực tiếp.
- [ ] Hoàn thiện data deletion, account deletion và consent records.
- [ ] Chuẩn bị onboarding script, FAQ support và incident escalation bằng tiếng Việt.
- [ ] Tạo capability flags để landing không quảng cáo feature chưa release.

Exit criteria:

- [ ] Internal beta checklist pass lại sau các bản sửa.
- [ ] Có thể support một khách bằng log/admin view mà không cần SSH vào production.
- [ ] Customer data và founder/demo data được tách workspace và quyền rõ ràng.
- [ ] Gate F được sign-off trước khi gửi lời mời beta.

### Tuần 12 — Closed beta khách hàng Việt Nam

Mục tiêu: onboard 5–10 khách cùng một ngành và thu dữ liệu quyết định sản phẩm.

Launch:

- [ ] Onboard theo từng cohort nhỏ, không mở public signup hàng loạt.
- [ ] Theo dõi activation và support trực tiếp trong 48 giờ đầu.
- [ ] Daily review P0/P1; weekly product interview.
- [ ] Đo cost/draft, cost/published post và support time/workspace.
- [ ] Landing chỉ public các capability đã qua release gate.

Product decisions cuối tuần:

- [ ] Giữ hay đổi ngành pilot.
- [ ] Ưu tiên Google Business hay Zalo OA tiếp theo.
- [ ] Có đủ tín hiệu để làm lead pipeline/inbox không.
- [ ] Pricing 299K/599K có phù hợp cost và willingness-to-pay không.
- [ ] Tiếp tục closed beta, mở rộng cohort hay quay lại cải thiện activation.

Exit criteria:

- [ ] Có ít nhất 4 tuần kế hoạch đo retention sau launch.
- [ ] Có dữ liệu thật để quyết định P1, không quyết định theo prototype.
- [ ] Incident, feedback và cost đều có owner và nơi theo dõi.

## 6. Release gates

### Gate A — Contract & foundation

- [ ] CI chạy lint, type-check, tests, build và migration check. **Chạy được bằng
  tay** (xem README "Kiểm tra nhanh") nhưng chưa có CI tự động — chưa đạt.
- [x] OpenAPI client generate và compile repeatably.
- [x] Local stack có tài liệu chạy một lần, không cần kiến thức ngầm.

### Gate B — Design-complete

- [ ] Tất cả prototype có implementation code-native. **Còn thiếu:** AI Marketing
  demo (5/6 prototype đã có code — demo này là sales-only, không phải core app).
- [ ] Desktop/mobile fidelity được design sign-off. *(Cần founder/QA — không tự tick.)*
- [ ] Keyboard, focus, loading, empty, error và reduced-motion states có đủ.
  Focus outline, reduced-motion, empty/error/loading component đã có; **còn thiếu**
  keyboard walkthrough thủ công và automated a11y check.

### Gate C — Core value loop

- [x] User thật tạo workspace, upload và nhận draft từ worker — verify tay:
  signup → onboarding → upload ảnh lên MinIO → job `drafts_ready` → 3 draft.
- [x] Draft sửa/duyệt/lên lịch đúng state machine — sửa tạo version mới, duyệt
  lúc 20:00 VN rơi đúng ô hôm nay trên lịch, duyệt lại trả 409.
- [x] Tenant isolation và audit tests pass (128 test backend). **Lưu ý:** pass
  khi chạy tay, chưa có CI tự động — xem Gate A.

### Gate D — Safe publishing

- [x] Facebook OAuth/token encryption/reconnect chạy thật — `/connections/*` với
  signed state chống CSRF, token mã hoá Fernet không bao giờ ra response, và UI
  nối/nối lại/ngắt kênh ở onboarding bước 2 + `/cai-dat`.
- [x] Scheduler + worker + adapter publish không duplicate — beat → `dispatch_due`
  → `run_due`, chống trùng bằng unique constraint + `FOR UPDATE SKIP LOCKED`, và
  task không nhận `content_item_id` qua message.
- [x] Error classification và manual recovery đã kiểm thử — ba loại lỗi đi ba
  đường khác nhau, `POST /content/publish-jobs/{id}/retry` có guard chỉ nhận
  `dead_letter`, 50 test cho riêng phần này.
- [ ] **Chưa đóng Gate:** một bài thật lên Facebook Page pilot. Toàn bộ đường đi
  đã chạy đầu-cuối với `FakePublisher` và Graph API giả ở tầng socket
  (`httpx.MockTransport`); phần chưa kiểm là Graph API thật, cần Facebook app +
  Page pilot (§12). Không tick Gate D trước khi có bài thật — đúng tinh thần
  "không tích vì đã scaffold" ở §Quy ước theo dõi.

### Gate E — Founder internal beta

- [ ] E2E happy/error paths pass trên staging.
- [ ] Không lỗi P0/P1, có backup/restore và incident runbook.
- [ ] Founder dùng thật 7 ngày, tối thiểu 10 content jobs và 5 publish jobs.
- [ ] Founder tự recovery được các lỗi thông thường qua UI.

### Gate F — Customer closed beta

- [ ] Tất cả vấn đề P0/P1 từ founder dogfooding đã đóng và retest.
- [ ] Tenant isolation, account/data deletion và support tooling đã kiểm thử.
- [ ] Public copy không hứa capability chưa release.
- [ ] Có onboarding/support flow bằng tiếng Việt và owner trực trong cohort đầu.

## 7. Definition of Done

Một feature chỉ được coi là hoàn thành khi:

- [ ] Có acceptance criteria và owner rõ.
- [ ] Dependency vẫn một chiều; không import xuyên private boundary của module.
- [ ] Business rule nằm trong domain/application, không nằm riêng ở UI/router/adapter.
- [ ] UI đúng prototype hoặc có design decision ghi lại lý do khác.
- [ ] Có loading, empty, error, permission và responsive states liên quan.
- [ ] API contract và authorization behavior được test.
- [ ] Query scope theo workspace nếu có dữ liệu tenant.
- [ ] Action nhạy cảm có audit event.
- [ ] Secret/token/PII không xuất hiện trong frontend hoặc log.
- [ ] Unit/integration test pass; critical path có E2E coverage.
- [ ] Observability đủ để support debug không cần đọc DB thủ công.
- [ ] Không thêm service/cache/queue/abstraction nếu chưa có boundary hoặc bottleneck rõ.
- [ ] Tài liệu vận hành và user-facing copy được cập nhật.

## 8. Test strategy

Frontend:

- [x] Component tests cho form, stateful controls và approval actions — form
  đăng nhập, onboarding và approval (duyệt lẻ, duyệt hết, 409, partial failure)
  đều có test chạy qua transport-layer mock.
- [x] Integration tests cho feature với generated API client được mock ở transport
  layer (`login-screen.test.tsx` mock `fetch`, không mock module app). Lưu ý:
  `publicApiClient` phải gọi `globalThis.fetch` tại thời điểm request — mặc định
  của openapi-fetch chốt `fetch` lúc tạo client, khiến mock không chặn được và
  test lặng lẽ gọi backend thật.
- [ ] Visual regression cho các viewport chuẩn và 6 prototype.
- [ ] E2E bằng browser cho auth, onboarding và content lifecycle.
- [ ] Automated accessibility check + keyboard walkthrough thủ công.

Backend:

- [ ] Unit tests cho state machine, quota, adapters và prompt-output validation.
- [ ] Repository integration tests với PostgreSQL thật.
- [ ] Contract tests cho OpenAPI/error envelope.
- [ ] Tenant isolation tests bắt buộc ở mọi domain mới.
- [x] Worker/scheduler tests cho retry, idempotency, locking và dead-letter —
  `test_publish_flow.py` (29), `test_publish_router.py` (13),
  `test_scheduler_wiring.py` (8). **Chưa xong:** test hai session Postgres song
  song thật cho `SKIP LOCKED` (xem Tuần 6), và test cho retry của content job.
- [ ] Security tests cho OTP, JWT refresh, OAuth state và token redaction.

Release:

- [ ] Migration rehearsal trên snapshot staging.
- [ ] Backup/restore rehearsal.
- [ ] End-to-end publish trên tài khoản Facebook pilot.
- [ ] Smoke tests sau deploy cho web, API, worker và scheduler.

## 9. Chỉ số thành công

Activation:

- [ ] ≥70% user pilot tạo được draft đầu tiên trong ngày onboarding.
- [ ] Median time signup → first draft dưới 10 phút.
- [ ] Tỷ lệ connect Facebook thành công ≥85% với user đủ quyền.

Content value:

- [ ] Draft ready p95 dưới 90 giây.
- [ ] ≥60% draft được duyệt với mức chỉnh sửa thấp.
- [ ] ≥50% workspace tạo hoặc duyệt nội dung mỗi tuần sau 4 tuần.

Reliability:

- [ ] Publish success ≥95% cho job hợp lệ.
- [ ] Duplicate publish = 0.
- [ ] Cross-tenant data incident = 0.
- [ ] Có thể truy vết 100% failed jobs bằng correlation ID.

Economics:

- [ ] Theo dõi cost mỗi content job, mỗi approved draft và mỗi published post.
- [ ] AI + infrastructure cost/workspace nằm trong biên của gói giá dự kiến.
- [ ] Quota/alert hoạt động trước khi có thể vượt ngân sách tháng.

## 10. Rủi ro và biện pháp giảm thiểu

| Rủi ro | Tác động | Biện pháp |
|---|---|---|
| Facebook app review/quyền API chậm | Chặn publish pilot | Mở app review từ Tuần 1; có adapter sandbox/fake nhưng không gọi đó là production |
| Email provider chưa chốt | Chặn luồng đặt lại mật khẩu (đăng ký/đăng nhập không bị chặn) | Dùng `debug_code` khi debug; chốt vendor trước closed beta |
| Landing hứa nhiều hơn sản phẩm | Mất niềm tin, rủi ro pháp lý | Capability flags cho copy; review claim ở Tuần 3 và Tuần 9 |
| LLM output không ổn định | Draft lỗi hoặc claim nguy hiểm | Structured output, schema validation, banned claims, retry giới hạn và human approval |
| Cross-tenant leak | Sự cố nghiêm trọng | Tenant-scoped repository, deny-by-default và CI isolation tests |
| Publish trùng | Ảnh hưởng thương hiệu khách | Unique idempotency key, row lock, platform post ID và reconciliation |
| Token cost tăng âm thầm | Mất margin | event log usage, quota theo workspace, threshold alert và model routing |
| Scope social listening/CRM phình | Trễ vòng giá trị chính | Pilot dùng intake thủ công; chỉ code sau khi chứng minh nhu cầu |
| Sản phẩm đúng kỹ thuật nhưng không hợp thói quen người Việt | Activation thấp | Founder dogfooding, cohort một ngành, tiếng Việt đời thường, mobile/mạng yếu và support qua kênh quen thuộc |
| Một dev phải làm toàn bộ | Timeline 12 tuần không thực tế | Giữ dependency order, cắt P1 và đổi estimate thành 16–22 tuần |

## 11. Backlog ưu tiên ngay

Thứ tự triển khai tiếp theo từ code hiện tại:

- [x] Chuyển App Shell thành shared app layout và tạo route cho 5 tab
  (`app/(app)/layout.tsx` + 5 route, nav active-state theo `usePathname`).
- [x] Dựng tab Tạo nội dung bằng fixture với đầy đủ generating/approval states
  (drop zone, chip liệu thô, toggle review_first/full_auto, 5 draft card, duyệt lẻ + duyệt hết).
- [x] Dựng Lịch đăng và đồng bộ state từ draft đã duyệt (lưới tuần 7 ngày,
  post theo kênh, badge scheduled/published/failed).
- [x] Dựng Khách tiềm năng và Báo cáo bằng fixture (lead card + suggested reply
  + FAQ strip; stat card, bar chart tuần, attribution bar, Havi insight).
- [x] Tạo UI primitives và test setup trước khi nhân rộng thêm màn
  (`components/ui/`: Button, Card, Badge, Input, OtpInput, Empty/Error/Loading;
  Vitest + React Testing Library).
- [x] Sinh TypeScript client từ OpenAPI scaffold (`npm run generate:api` →
  `apps/web/src/lib/api-client/`; chưa có feature nào nối vào vì backend còn 501).
- [x] Scaffold local PostgreSQL/Redis/object storage + Alembic (`docker-compose.yml`
  ở root + `apps/backend/migrations/`; verify bằng smoke-test migration thật, chưa
  có domain model/table nghiệp vụ nào — `target_metadata` vẫn `None` chờ Tuần 4).
- [x] Dựng Auth và Onboarding design-complete (đăng nhập email+mật khẩu, đăng ký,
  quên/đặt lại mật khẩu, onboarding 3 bước) bằng fixture, chưa nối API thật.
  **Chưa làm:** demo AI Marketing (sales-only, không phải core app — để P1/P2),
  keyboard/focus walkthrough thủ công,
  design sign-off (cần founder/QA, không tự tick được).
- [x] Nối onboarding và tab Tạo nội dung vào API thật — vòng nạp liệu → sinh
  bài → duyệt đã chạy thật từ trình duyệt, không còn fixture.
  **Việc tiếp theo:** editor + version history, rồi nối Lịch đăng (Tuần 6), sau
  đó Facebook OAuth/publish (Tuần 7) để đóng Gate D.
- [x] Nối editor + version history và Lịch đăng vào API thật — **Gate C đóng**:
  vòng nạp liệu → sinh bài → sửa → duyệt → lên lịch chạy thật từ trình duyệt.
  **Việc tiếp theo:** Facebook OAuth + adapter publish (Tuần 7, Gate D).
- [x] Facebook OAuth (`/connections/*`) + adapter Graph API publish — backend
  Tuần 7 xong: nối/nối lại/ngắt kênh, token mã hoá không ra response, đăng bài
  chữ/một ảnh/nhiều ảnh, phân loại lỗi và redaction token.
- [x] Đóng ba trong bốn việc còn lại của Tuần 7: (1) Celery beat gọi
  `publish_service_factory` theo lịch — `dispatch_due_posts` tạo job rồi giao
  `publish.run_due` chạy, cộng lưới an toàn mỗi phút cho job đang chờ backoff;
  (2) Connection UI + reconnect CTA — `features/connections/` dùng chung cho
  onboarding bước 2 và tab Cài đặt mới, đồng thời bỏ chip kênh giả và tên tiệm
  hardcode trong sidebar; (3) `POST /content/publish-jobs/{id}/retry` có guard
  chỉ nhận `dead_letter`. Backend 263 test, web 82 test.
  **Việc tiếp theo (việc thứ 4, chặn Gate D):** đăng thử một bài thật lên Page
  pilot bằng Development mode — cần Facebook app + Page, xem §12. Sau đó là UI
  đọc `/content/publish-jobs` để chủ tiệm thấy bài lỗi và bấm "Thử lại" (hiện
  endpoint đã có nhưng chưa màn nào gọi), rồi Dashboard thật (Tuần 8).
- [x] Dựng Landing Page ở `/gioi-thieu` với claim đã rà theo capability thật.
- [x] Bắt đầu persistence/auth thật (`/auth/*`, `/workspaces/*`, `/brand-profile`
  chạy thật trên Postgres). Lưu ý: làm trước khi Gate B được sign-off chính thức
  — Gate B cần design review của founder/QA, xem §6.

## 12. Quyết định cần chốt

Các quyết định này có deadline để không chặn roadmap:

| Trạng thái | Quyết định | Deadline | Owner đề xuất |
|---|---|---:|---|
| [ ] | Ngành pilot đầu tiên | Trước Tuần 1 | Product |
| [ ] | Email provider gửi mã đặt lại mật khẩu và chi phí | Trước Tuần 9 | Backend/Product |
| [ ] | Cloud region, Postgres, Redis, object storage | Cuối Tuần 1 | Engineering |
| [ ] | Facebook developer app + quyền cần xin | Trong Tuần 1 | Product/Backend |
| [ ] | Web responsive breakpoint support chính thức | Cuối Tuần 2 | Frontend/Design |
| [~] | Data retention và media deletion policy — Privacy đã ghi 30 ngày; cần Legal thẩm định + code endpoint xoá | Cuối Tuần 3 | Product/Legal |
| [ ] | `full_auto` có xuất hiện trong pilot hay bị khóa | Cuối Tuần 3 | Product/Security |
| [ ] | Engagement metrics nào Facebook cho phép lấy | Trước Tuần 8 | Backend/Product |
| [ ] | Pricing/trial claim được public | Trước Tuần 12 | Product/Finance |
| [ ] | Workspace và Facebook Page dùng cho founder dogfooding | Trước Tuần 9 | Founder/Product |
| [ ] | Cohort khách beta đầu tiên và kênh support | Trước Tuần 11 | Founder/Product |

Roadmap được re-plan sau mỗi release gate, nhưng không thay đổi các nguyên tắc
approval, tenant isolation, official API và idempotent publishing.
