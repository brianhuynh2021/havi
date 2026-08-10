# Havi — Cấu hình & triển khai

> Tài liệu vận hành: cần chạy gì, khai biến nào, và **cái gì sai thì im lặng**.
>
> Nguyên tắc viết file này: chỉ ghi những thứ **không suy ra được từ code**. Danh
> sách biến đầy đủ ở `apps/backend/.env.example`; cách chạy local ở `README.md`.
> Đây là chỗ ghi các cái bẫy — thứ mà thiếu nó thì mọi thứ trông như đang chạy.

## 1. Cấu hình "chỉ dành cho local"

Các biến dưới đây làm Havi **giả lập** thay vì làm thật. Chúng đều có validator
ném lỗi lúc khởi động khi `HAVI_ENV != local`, nên không thể lỡ để sót lên staging
— nhưng phải hiểu vì sao mới biết cần kiểm gì sau khi deploy.

| Biến | Mặc định | Bật true nghĩa là | Sai kiểu gì |
|---|---|---|---|
| `HAVI_USE_MOCK_LLM` | `true` | Draft là văn mẫu, không gọi model | Chủ tiệm đăng văn mẫu lên Facebook thật mà tưởng AI viết |
| `HAVI_USE_FAKE_PUBLISHER` | `true` | Không có bài nào lên Facebook | Mọi bài báo "đã đăng", dashboard xanh, **Trang trống trơn** |
| `HAVI_DISABLE_RATE_LIMIT` | `false` | Không giới hạn gì | Không có dấu hiệu nào; brute force mật khẩu không bị chặn, script lỗi đốt hết quota LLM trong vài phút |
| `HAVI_EMAIL_PROVIDER=debug` | `debug` | Reset password trả `debug_code`, không gửi email thật | User staging/production không nhận được mã đặt lại mật khẩu |

**Mặc định của hai cờ đầu là `true`** — tức nếu chỉ copy `.env.example` rồi deploy
thì backend sẽ **không khởi động** (validator chặn). Đó là chủ ý: thà không chạy
còn hơn chạy giả.

Sau khi deploy, kiểm bằng log khởi động: nếu thấy dòng cảnh báo
`Publish đang chạy FAKE` hoặc `LLM đang chạy MOCK` ở staging thì có gì đó sai.

Email cũng theo cùng nguyên tắc: local dùng `HAVI_EMAIL_PROVIDER=debug` để test
quên mật khẩu không cần vendor. Khi `HAVI_ENV=staging|production`, backend sẽ
không khởi động nếu vẫn để debug. Cấu hình SMTP tối thiểu:

```bash
HAVI_EMAIL_PROVIDER=smtp
HAVI_EMAIL_FROM=no-reply@domain-cua-anh.com
HAVI_SMTP_HOST=smtp.domain-cua-anh.com
HAVI_SMTP_PORT=465
HAVI_SMTP_USERNAME=...
HAVI_SMTP_PASSWORD=...
HAVI_SMTP_USE_TLS=true
```

Ở staging/production, `/auth/password-reset/request` không bao giờ trả
`debug_code`; mã chỉ đi qua email provider.

## 2. Facebook — bốn thứ phải khai, thiếu một cái là chết theo một kiểu khác

Đây là phần mất nhiều thời gian nhất khi dựng lần đầu, vì Facebook không nói rõ
thiếu cái gì. Làm **đúng thứ tự** này:

### 2.1. App Domains (App settings → Basic)

Điền **chỉ tên miền**, không có `https://`, không có đường dẫn:

```
domain-cua-anh.com
```

- Thiếu → màn cấp quyền báo **"Can't load URL"** trước cả khi hỏi quyền.
- Facebook **chặn lưu App Domains khi thiếu Privacy Policy URL** — điền
  `https://domain-cua-anh.com/bao-mat` trước, rồi mới điền App Domains.
- **Không sửa được qua Graph API** (`(#10) Changing app settings through API calls
  has been disabled`) — phải bấm trên dashboard.

### 2.2. Valid OAuth Redirect URIs (Facebook Login → Settings)

Điền **URL đầy đủ**, khớp từng ký tự với `HAVI_FACEBOOK_REDIRECT_URI`:

```
https://api.domain-cua-anh.com/connections/facebook/callback
```

- Đây là ô **khác** với App Domains ở trên. Dán URL đầy đủ vào App Domains sẽ lỗi,
  và dán tên miền vào ô này cũng lỗi.
- Ô **"Redirect URI to check"** ở đầu trang chỉ là công cụ tra cứu — dán vào đó
  không lưu gì. Dán vào ô danh sách rồi bấm **Enter** cho thành thẻ, rồi Save.
- **"Enforce HTTPS" đã bị Meta khoá** (công tắc mờ, không tắt được), nên
  `http://localhost` không còn là redirect URI hợp lệ. Local phải dùng tunnel:

  ```bash
  brew install cloudflared
  cloudflared tunnel --url http://localhost:8000
  ```

  URL `trycloudflare.com` **đổi mỗi lần chạy lại tunnel** — đổi thì phải khai lại
  cả `HAVI_FACEBOOK_REDIRECT_URI`, App Domains và Valid OAuth Redirect URIs.

### 2.3. Use cases → quyền (Use cases → Manage everything on your Page)

Ba quyền Havi cần, cả ba phải ở trạng thái **"Ready for testing"**:

| Quyền | Dùng để |
|---|---|
| `pages_show_list` | Đọc danh sách Page chủ tiệm quản lý |
| `pages_read_engagement` | Đọc tên Page (bắt buộc khi lấy Page token qua `/me/accounts`) |
| `pages_manage_posts` | Đăng bài |

Quyền chưa bật ở đây thì **không hiện ra để tick** ở bước Configuration bên dưới.

### 2.4. Configuration (Facebook Login for Business → Configurations)

App tạo mới hiện nay mặc định là **Facebook Login for Business**, loại này khai
quyền trong một *Configuration* và request gửi `config_id` — **không** gửi `scope`.
Gửi `scope` thì Facebook vẫn hiện màn cấp quyền rồi mới trả `Invalid Scopes` ở
bước callback, nên rất khó đoán.

Tạo configuration với: **Login variation** = General, **Access token** = User
access token, **Permissions** = đúng ba quyền trên (bỏ tick
`business_management`, `pages_manage_engagement` — Havi không dùng).

Copy Configuration ID vào `HAVI_FACEBOOK_CONFIG_ID`.

App dùng Facebook Login *thường* thì để trống biến này — code tự đi đường cũ
(gửi `scope`).

### 2.5. Ai được dùng khi chưa qua App Review

Development mode cho **người có vai trò trong app** (Administrator, Developer,
Tester) nối Page của chính họ và đăng thật — đủ cho closed beta 5–10 tiệm, thêm
thủ công từng người ở **App roles → Roles**.

Lưu ý: Administrator **đã bao gồm** quyền của Tester, và Facebook không cho hạ
Admin cuối cùng xuống Tester (`You must have at least one admin`).

App Review + Business Verification (cần pháp nhân) chỉ bắt buộc khi mở public
signup.

## 3. Quota token & rate limit

### Quota — đo bằng token, không bằng tiền

Trần theo gói, khai trong `domain/policies/quota.py`:

| Gói | Trần/tháng | Ước lượng |
|---|---:|---|
| `trial` | 100.000 token | ~25 bài |
| `tiem_nho` | 500.000 token | ~125 bài |
| `toan_dien` | 2.000.000 token | ~500 bài |

**Vì sao token chứ không phải tiền:** mỗi provider một đơn giá và giá LLM đổi liên
tục, nên một bảng giá hardcode cho ra con số *nhìn như đúng* mà sai — tệ hơn không
có quota, vì nó tạo cảm giác đang kiểm soát chi phí trong khi không. Số token là
sự thật tuyệt đối trong `event_log`. Muốn ra tiền thì nhân ngoài, ở chỗ định giá gói.

Quota reset theo mốc dương lịch **giờ VN** (không phải 30 ngày từ lúc đăng ký).
Vượt trần → `429` kèm `Retry-After` và số liệu thật.

**Đây là số cần đo lại sau pilot** (ROADMAP §9 Economics), không phải hằng số vĩnh
viễn — sửa ở đúng một chỗ `MONTHLY_TOKEN_QUOTA`.

### Rate limit — cần Redis, và fail-open

Khai trong `domain/policies/rate_limits.py`. Auth theo **IP**, upload/content theo
**workspace**.

Hai điều phải biết khi lên staging:

1. **Redis hỏng thì cho qua (fail-open)**, không chặn. Rate limit là lớp bảo vệ,
   fail-closed sẽ biến một sự cố Redis thành outage toàn phần. Đánh đổi: trong lúc
   Redis chết thì **không có giới hạn nào** và không có dấu hiệu gì trên UI — nên
   **alert cho Redis là bắt buộc**, không phải tuỳ chọn.

2. **Phải chạy sau reverse proxy.** Rate limit theo IP đọc `X-Forwarded-For`, mà
   header đó do client gửi nên giả mạo được. Chỉ an toàn khi có proxy mình kiểm
   soát ghi đè header. Chạy trần ra internet thì kẻ tấn công đổi header mỗi lượt là
   thoát giới hạn hoàn toàn.

## 4. Bốn process phải chạy

Thiếu process nào thì hệ thống vẫn "chạy" nhưng mất một mảng chức năng, im lặng:

| Process | Lệnh | Thiếu thì |
|---|---|---|
| API | `uvicorn api.main:app --host 0.0.0.0 --port 8000` | Không có gì hoạt động (rõ ràng) |
| Celery worker | `celery -A worker.celery_app:celery_app worker -l info` | Bấm "Để Havi viết" xong job treo ở `queued` mãi; bài đã duyệt không bao giờ lên Trang |
| Celery beat | `celery -A scheduler.beat:celery_app beat -l info` | Bài đã duyệt nằm mãi ở `scheduled`, **không có lỗi nào** |
| Web | `next start` | Chủ tiệm không vào được |

Cả worker và beat cần extra `queue`: `uv sync --extra queue`.

Beat có 5 lịch; 3 trong số đó vẫn là khung `NotImplementedError` (refresh token,
CRM nudge, engagement) — thấy traceback của chúng trong log worker là **đã biết**,
không phải regression. Xem ROADMAP Tuần 8+.

## 5. Migration

```bash
uv run alembic upgrade head    # trước khi khởi động API bản mới
uv run alembic check           # phải sạch: model và DB đã khớp
```

Chưa có backup/restore rehearsal và rollback strategy — **chưa được mời khách beta
trước khi có** (ROADMAP §3 "Hạ tầng bắt buộc trước beta").

## 6. Secret — cái nào đổi được, cái nào không

| Secret | Đổi được không |
|---|---|
| `HAVI_JWT_SECRET` | Đổi được, nhưng mọi người đang đăng nhập bị đá ra (token cũ không verify được) |
| `HAVI_TOKEN_ENCRYPTION_KEY` | **Đổi là mất hết token nền tảng đã lưu** — mọi chủ tiệm phải nối lại kênh. Thiếu khoá thì code ném lỗi chứ không lưu plaintext. |
| API key LLM | Đổi tự do, không ảnh hưởng dữ liệu |
| Facebook client secret | Đổi được; token Page đã cấp vẫn dùng được tới khi hết hạn |

Chưa có key rotation plan (ROADMAP §3) — `HAVI_TOKEN_ENCRYPTION_KEY` hiện là khoá
đơn, không có versioning, nên chưa xoay được mà không mất token.

## 7. Checklist trước khi mở cho khách

Rút từ ROADMAP §3 "Hạ tầng bắt buộc trước beta" — **không mời khách beta nếu còn
mục nào chưa xong**:

- [ ] `HAVI_ENV=staging|production` (validator tự chặn ba cờ local)
- [ ] `alembic upgrade head` xong, `alembic check` sạch
- [ ] Đủ 4 process, và **beat có chạy** (kiểm bằng cách duyệt một bài rồi xem nó
      có lên Trang không — không có lỗi nào để dựa vào)
- [ ] Facebook: App Domains + Redirect URI + 3 quyền + Configuration ID
- [ ] Reverse proxy ghi đè `X-Forwarded-For` (nếu không, rate limit theo IP vô nghĩa)
- [ ] Email provider thật cho password reset; `HAVI_EMAIL_PROVIDER` không phải `debug`
- [ ] **Alert cho Redis** — rate limit fail-open nên Redis chết là mất giới hạn mà
      không có dấu hiệu gì
- [ ] Backup tự động **và** đã restore thử được (chưa làm)
- [ ] Tenant isolation test pass trong CI (chưa có CI)
- [ ] Đăng thử một bài thật lên Page nháp trước khi cho khách vào
