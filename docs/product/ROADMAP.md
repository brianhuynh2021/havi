# Havi — Product & Engineering Roadmap

> Phiên bản: 2026-08-03
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
| Landing Page | Hero, 4 trạm, ngành, pricing, CTA | Tuần 3 | Tuần 12 sau khi rà soát claim |
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
- [x] Celery worker/Beat scaffold.
- [x] 95 backend tests đang pass (31 contract/state-machine/provider-router + 64
  auth/workspace/brand-profile/media/content chạy thật trên Postgres + MinIO);
  Ruff đang pass.

Architecture/docs:

- [x] Monorepo boundary, frontend/backend ownership và future split strategy đã chốt.
- [x] Sơ đồ hệ thống, frontend modules và content state machine đã có.
- [x] Handoff ghi đầy đủ fidelity, interaction và approval workflow.

### Chưa hoàn thành

- [ ] Frontend routes, interaction thật và visual regression tests.
- [x] Generated TypeScript API client.
- [x] PostgreSQL models/repositories cho auth, workspace/member và brand profile;
  Alembic migrations thật; tenant isolation có test (403 khi JWT hợp lệ nhưng
  không phải thành viên). **Chưa xong:** repository cho content/media/calendar/
  inbox/leads.
- [x] JWT access + refresh token xoay vòng, đăng ký/đăng nhập email + mật khẩu
  (Argon2), đặt lại mật khẩu qua mã 6 số. **Chưa xong:** email provider thật
  (dùng `debug_code` khi `HAVI_DEBUG=true`), endpoint logout/revoke session.
- [x] Object storage (MinIO) đã dùng thật: signed upload + magic-byte validation
  ở `/media`. Redis + Celery đã dùng thật: `havi.content.generate_drafts` chạy
  Content Engine trong worker.
- [x] LLM content pipeline (multi-provider, Gemini ưu tiên) + structured output
  validation + ghi token vào `event_log`. **Chưa có:** quota chặn theo workspace,
  và cost tính bằng tiền.
- [ ] OAuth/token encryption và adapter publish Facebook.
- [ ] Scheduler/retry/idempotency/dead-letter production behavior.
- [ ] CI/CD, staging, observability, alerting và runbook.
- [ ] E2E test cho hành trình signup → draft → approve → publish → report.

Tất cả endpoint nghiệp vụ hiện chỉ khóa contract và trả `501 Not Implemented`.

### Hạ tầng bắt buộc trước beta

Code hiện tại **chưa đủ để chạy beta thật**. Trước khi chính founder dùng thử,
hệ thống phải có đủ bốn lớp dữ liệu/vận hành sau:

PostgreSQL:

- [x] `users`, `otp_challenges`, `refresh_sessions` (migration `c5a2a7713af1`,
  `eb7685b1cb83` đổi email thành danh tính chính và SĐT thành tuỳ chọn).
- [x] `workspaces`, `workspace_members`, `brand_profiles` — có repository + router
  thật (`/workspaces/*`, `/brand-profile`), test chạy trên Postgres.
- [ ] `platform_connections` với token mã hóa.
- [x] `media_assets`, `content_jobs`, `content_items`, `content_item_versions`
  (migration `a974c194ff2c`, `32712ea2080b`).
- [x] `event_log` — insert thật qua `EventLogRepository`. **Chưa có:**
  `publish_jobs`, `engagement_snapshots`.
- [x] Alembic migrations, indexes, foreign keys cho các bảng auth/workspace ở
  trên (`alembic check` sạch). **Chưa xong:** tenant-scoped repository cho các
  domain còn lại, và test tenant isolation.

Redis/job queue:

- [ ] Celery broker/result backend hoặc cơ chế tương đương.
- [ ] Rate limit OTP/content generation.
- [ ] Job retry, lock ngắn hạn và dead-letter handling.
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
- [ ] Onboarding ngành, brand voice cơ bản và kết nối Facebook Page.
- [ ] Upload ảnh + nhập text; ghi âm có thể để sau nếu ảnh/text chưa ổn định.
- [ ] Một content job sinh nhiều draft theo kênh bằng structured output.
- [ ] Editor, version history, duyệt lẻ, duyệt hàng loạt và lên lịch.
- [ ] Facebook Page OAuth + publish bằng API chính thức.
- [ ] Calendar và trạng thái publish đầy đủ.
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
- [ ] Consent, quyền xóa dữ liệu, opt-out và chính sách lưu dữ liệu phải phù hợp quy định Việt Nam hiện hành.
- [ ] Support beta dùng kênh quen thuộc với cohort, ưu tiên Zalo/điện thoại thay vì chỉ email ticket.
- [ ] Pricing hiển thị bằng VND và chỉ public sau khi đo được chi phí AI/hạ tầng trên khách Việt thật.

## 5. Kế hoạch thực thi 12 tuần

Ước lượng cho 1 frontend, 1 backend và product/design/QA bán thời gian. Nếu chỉ
có một full-stack developer, dùng cùng dependency order nhưng dự kiến 16–22 tuần.

### Tuần 1 — Khóa nền tảng frontend và contract

Mục tiêu: app có route structure ổn định, API contract dùng được và mọi thay đổi
sau đó đi qua cùng một quality gate.

Frontend:

- [x] Chốt route groups: `(app)`, `(auth)`, `(onboarding)`. **Chưa có** group
  `public` vì Landing Page chưa dựng.
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

- [ ] Landing Page responsive, anchor navigation, pricing và CTA.
- [x] Auth flows: email login, signup (tên + email + mật khẩu), forgot/reset
  password qua mã 6 số trong email, resend countdown và success routes.
- [x] Onboarding 3 bước: industry, connections, learning state và first draft.
- [ ] AI Marketing demo theo persona cho sales/internal review.
- [x] Thêm reduced-motion behavior cho progress animation
  (`@media (prefers-reduced-motion: reduce)` ở mọi spinner).
- [ ] Tạo route guards mock: guest, needs onboarding và authenticated.

Product/legal:

- [ ] Rà soát landing claims: số kênh, tự động đăng, social listening, giá và trial.
- [ ] Ẩn hoặc đổi copy với capability chưa production-ready.
- [ ] Chốt Terms, Privacy và data retention placeholder trước closed beta.

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
  **Chưa xong:** content/media/... vẫn `501`, nên tenant isolation mới verify
  được ở workspace + brand-profile, chưa ở toàn bộ domain.
- [x] Workspace create/activate và onboarding completion state. `/workspaces`
  (CRUD), `/workspaces/{id}/activate` (đổi JWT), `/workspaces/{id}/members`
  (invite/list/remove, chặn xoá owner cuối) — `tests/test_workspace_flow.py`,
  9 case chạy thật trên Postgres.
- [x] Brand profile thật: `GET/PUT /brand-profile` (tone, banned_claims, faq,
  logo_url, brand_colors), tạo lazy theo `industry` của workspace ở lần gọi đầu
  — `tests/test_brand_profile_flow.py`, 7 case chạy thật. **Chưa xong:** chưa có
  cache profile cho worker (worker sẽ đọc trực tiếp DB), và PUT hành xử như PATCH
  nên không xoá được `logo_url` về null.
- [ ] Encrypt sensitive fields bằng application key management.

Frontend:

- [ ] Nối auth API, session bootstrap, refresh và logout.
- [ ] Route guards thật cho guest/onboarding/app.
- [ ] Nối industry/brand profile onboarding.
- [ ] Xử lý loading, sai mật khẩu, mã hết hạn, throttled và network failure.
- [ ] Thêm screen chọn workspace khi user có nhiều workspace.

Tests/security:

- [ ] Integration test chứng minh workspace A không đọc/sửa workspace B.
- [x] Tests cho brute force mã đặt lại mật khẩu, refresh token rotation + chặn tái
  sử dụng. **Chưa xong:** logout revoke (chưa có endpoint).
- [x] Không log OTP, JWT, refresh token hoặc PII nhạy cảm (chỉ lưu hash trong DB).

Exit criteria:

- [ ] Signup (email) → onboarding → app chạy end-to-end với DB thật.
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

- [ ] Upload progress, cancel/retry và preview.
- [ ] Tạo content job từ ảnh/text và poll job status.
- [ ] Mapping queued/processing/drafts_ready/failed vào đúng UI prototype.
- [ ] Không dùng timer 2.9s giả lập khi đã nối API thật.

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

- [ ] Content item update tạo version mới, không overwrite lịch sử.
- [ ] Enforce state transitions trong service/domain layer.
- [ ] Single approve, reject, bulk approve và reschedule transactionally.
- [ ] Ghi `approved_by`, `approved_at` và audit event.
- [ ] Calendar là projection từ `content_item.scheduled_at`.
- [ ] Không cho reschedule item đã `published`.

Frontend:

- [ ] Nối draft editor, version history, approve/reject và bulk approve.
- [ ] Optimistic UI có rollback + toast khi backend từ chối.
- [ ] Nối calendar, timezone Asia/Ho_Chi_Minh và reschedule.
- [ ] Hiển thị rõ pending, approved, scheduled, publishing, published và failed.
- [ ] `full_auto` chỉ hiện như controlled setting; chưa mở cho pilot user nếu policy chưa chốt.

Tests:

- [ ] State-transition matrix tests.
- [ ] Concurrent approve/bulk approve tests.
- [ ] Timezone/DST-safe serialization tests dù Việt Nam không có DST.

Exit criteria:

- [ ] Không có API path đưa item chưa duyệt sang publish trong `review_first`.
- [ ] Version history và audit đủ để trả lời ai sửa/duyệt, lúc nào.
- [ ] Draft đã duyệt xuất hiện đúng ngày/giờ trên calendar.

### Tuần 7 — Facebook connection và publishing

Mục tiêu: đăng một bài đã duyệt lên Facebook Page đúng lịch và không trùng.

Backend/platform:

- [ ] Facebook OAuth start/callback với signed state và CSRF protection.
- [ ] Lưu token mã hóa; không trả token về frontend.
- [ ] Connection status: connected, expired, revoked; reconnect flow.
- [ ] Facebook adapter mapping text/media và normalize platform errors.
- [ ] Scheduler tạo publish job đến hạn.
- [ ] Worker publish với unique idempotency key, row lock và retry backoff.
- [ ] Phân loại temporary, auth-permission và validation-permanent errors.
- [ ] Dead-letter state + manual retry endpoint có guard.

Frontend:

- [ ] Connection UI trong onboarding/settings.
- [ ] Scheduled/publishing/published/failed states và hướng xử lý theo error class.
- [ ] Reconnect CTA khi token hết hạn hoặc mất quyền.
- [ ] Không hiển thị TikTok/Zalo/Maps là “đã nối” nếu chỉ là fixture.

Tests:

- [ ] Adapter tests với recorded/sandbox responses hợp lệ.
- [ ] Double-click, duplicate worker và retry không đăng hai bài.
- [ ] Token redaction tests trong logs/errors.

Exit criteria:

- [ ] Bài đã duyệt được đăng đúng lịch lên Facebook Page pilot.
- [ ] Retry không tạo duplicate post.
- [ ] Auth failure dẫn người dùng về reconnect, không retry vô hạn.

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

- [ ] Tất cả prototype có implementation code-native. **Còn thiếu:** Landing Page
  và AI Marketing demo (4/6 prototype đã có code).
- [ ] Desktop/mobile fidelity được design sign-off. *(Cần founder/QA — không tự tick.)*
- [ ] Keyboard, focus, loading, empty, error và reduced-motion states có đủ.
  Focus outline, reduced-motion, empty/error/loading component đã có; **còn thiếu**
  keyboard walkthrough thủ công và automated a11y check.

### Gate C — Core value loop

- [ ] User thật tạo workspace, upload và nhận draft từ worker.
- [ ] Draft sửa/duyệt/lên lịch đúng state machine.
- [ ] Tenant isolation và audit tests pass.

### Gate D — Safe publishing

- [ ] Facebook OAuth/token encryption/reconnect chạy thật.
- [ ] Scheduler + worker + adapter publish không duplicate.
- [ ] Error classification và manual recovery đã kiểm thử.

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

- [ ] Component tests cho form, stateful controls và approval actions.
- [ ] Integration tests cho feature với generated API client được mock ở transport layer.
- [ ] Visual regression cho các viewport chuẩn và 6 prototype.
- [ ] E2E bằng browser cho auth, onboarding và content lifecycle.
- [ ] Automated accessibility check + keyboard walkthrough thủ công.

Backend:

- [ ] Unit tests cho state machine, quota, adapters và prompt-output validation.
- [ ] Repository integration tests với PostgreSQL thật.
- [ ] Contract tests cho OpenAPI/error envelope.
- [ ] Tenant isolation tests bắt buộc ở mọi domain mới.
- [ ] Worker/scheduler tests cho retry, idempotency, locking và dead-letter.
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
  **Chưa làm:** Landing Page và demo AI Marketing (sales-only, không phải core
  app — để P1/P2), route guards mock, keyboard/focus walkthrough thủ công,
  design sign-off (cần founder/QA, không tự tick được).
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
| [ ] | Data retention và media deletion policy | Cuối Tuần 3 | Product/Legal |
| [ ] | `full_auto` có xuất hiện trong pilot hay bị khóa | Cuối Tuần 3 | Product/Security |
| [ ] | Engagement metrics nào Facebook cho phép lấy | Trước Tuần 8 | Backend/Product |
| [ ] | Pricing/trial claim được public | Trước Tuần 12 | Product/Finance |
| [ ] | Workspace và Facebook Page dùng cho founder dogfooding | Trước Tuần 9 | Founder/Product |
| [ ] | Cohort khách beta đầu tiên và kênh support | Trước Tuần 11 | Founder/Product |

Roadmap được re-plan sau mỗi release gate, nhưng không thay đổi các nguyên tắc
approval, tenant isolation, official API và idempotent publishing.
