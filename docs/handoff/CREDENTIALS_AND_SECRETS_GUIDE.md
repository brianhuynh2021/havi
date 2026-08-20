# Havi — Bảng Tổng Hợp Thông Tin Cấu Hình & Credentials (Hệ Thống & Nền Tảng)

> **Tài liệu bàn giao & vận hành bí mật**: Bản đồ chi tiết toàn bộ khoá bảo mật, tài khoản dịch vụ, cổng thanh toán và nền tảng liên kết của Havi.
> 
> *Lưu ý*: File `.env` chứa khoá thật được bảo vệ bởi `.gitignore` để không bị lộ lên mã nguồn mở GitHub. Bạn nên lưu trữ một bản sao an toàn vào Trình quản lý mật khẩu cá nhân (như Bitwarden / 1Password / Apple Keychain).

---

## 1. Cơ Sở Dữ Liệu & Hạ Tầng Local (Docker / macOS)

Tất cả các dịch vụ hạ tầng này chạy qua Docker Compose (`docker-compose.yml`) hoặc trực tiếp trên máy Mac:

| Dịch vụ | Tham số biến môi trường | Giá trị mặc định / Local | Ghi chú vận hành |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16** | `HAVI_DATABASE_URL` | `postgresql+psycopg://havi:havi@localhost:5432/havi` | User: `havi`<br>Pass: `havi`<br>DB: `havi`<br>Port: `5432` |
| **Redis 7** | `HAVI_REDIS_URL` | `redis://localhost:6379/0` | Port: `6379` (Session, Celery queue & Caching) |
| **MinIO Storage** (S3 Local) | `HAVI_MEDIA_ENDPOINT_URL`<br>`HAVI_MEDIA_PUBLIC_URL`<br>`HAVI_MEDIA_ACCESS_KEY`<br>`HAVI_MEDIA_SECRET_KEY`<br>`HAVI_MEDIA_BUCKET` | `http://localhost:9000`<br>`http://localhost:9000/havi-media`<br>`minioadmin`<br>`minioadmin`<br>`havi-media` | Web Console: `http://localhost:9001`<br>Lưu trữ hình ảnh, video ngắn, raw voice notes |

---

## 2. Khoá Mật Mã Nội Bộ (Cryptography & Security)

Các khoá này dùng để bảo vệ dữ liệu chủ tiệm trong database:

| Biến môi trường | Mục đích sử dụng | Cơ chế an ninh |
| :--- | :--- | :--- |
| `HAVI_JWT_SECRET` | Ký và xác thực JSON Web Token khi đăng nhập | Thuật toán HS256, tự động kiểm tra token hết hạn |
| `HAVI_TOKEN_ENCRYPTION_KEY` | Khóa đối xứng AES-128 Fernet | **Tối quan trọng**: Mã hóa toàn bộ Access Token của Facebook / TikTok / Google trước khi ghi vào PostgreSQL |

---

## 3. Cổng AI Đa Mô Hình (LLM Engine)

Havi tích hợp cơ chế tự động Fallback linh hoạt giữa các nhà cung cấp AI:

| Nền tảng AI | Biến môi trường | Nơi quản lý & Lấy Key mới | Model khuyên dùng |
| :--- | :--- | :--- | :--- |
| **Google Gemini** | `HAVI_GEMINI_API_KEY`<br>`HAVI_GEMINI_MODEL` | [Google AI Studio](https://aistudio.google.com/) | `gemini-2.5-flash` / `gemini-1.5-pro` |
| **Anthropic Claude** | `HAVI_ANTHROPIC_API_KEY`<br>`HAVI_ANTHROPIC_MODEL` | [Anthropic Console](https://console.anthropic.com/) | `claude-3-5-sonnet-20241022` |
| **OpenAI GPT** | `HAVI_OPENAI_API_KEY`<br>`HAVI_OPENAI_MODEL` | [OpenAI Platform](https://platform.openai.com/) | `gpt-4o` / `gpt-4o-mini` |
| **Chế độ Mock Dev** | `HAVI_USE_MOCK_LLM=true` | Tích hợp sẵn trong source code | Bật khi test giao diện không tốn tiền API |

---

## 4. Kênh Mạng Xã Hội Đa Nền Tảng (OAuth & Publishing)

Toàn bộ các kênh liên kết của tiệm để Havi tự động đăng bài, tạo video ngắn 9:16 và trực Lead:

### A. Meta / Facebook Fanpage
* **Trang quản trị**: [Meta for Developers](https://developers.facebook.com/) $\rightarrow$ Chọn App Havi.
* **Các biến**:
  * `HAVI_FACEBOOK_CLIENT_ID`: App ID
  * `HAVI_FACEBOOK_CLIENT_SECRET`: App Secret
  * `HAVI_FACEBOOK_CONFIG_ID`: ID của Facebook Login for Business Configuration (chứa quyền `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`).
  * `HAVI_FACEBOOK_REDIRECT_URI`: `http://localhost:8000/connections/facebook/callback`

### B. Google Cloud (YouTube Shorts & Google Business Profile)
* **Trang quản trị**: [Google Cloud Console](https://console.cloud.google.com/) $\rightarrow$ APIs & Services $\rightarrow$ Credentials.
* **Các biến**:
  * `HAVI_GOOGLE_CLIENT_ID`: OAuth 2.0 Web Client ID
  * `HAVI_GOOGLE_CLIENT_SECRET`: Client Secret
  * `HAVI_YOUTUBE_REDIRECT_URI`: `http://localhost:8000/connections/youtube/callback`
  * `HAVI_GOOGLE_BUSINESS_REDIRECT_URI`: `http://localhost:8000/connections/google_business/callback`

### C. TikTok Business / Creator
* **Trang quản trị**: [TikTok for Developers](https://developers.tiktok.com/) $\rightarrow$ Manage Apps.
* **Các biến**:
  * `HAVI_TIKTOK_CLIENT_KEY`: Client Key của App
  * `HAVI_TIKTOK_CLIENT_SECRET`: Client Secret
  * `HAVI_TIKTOK_REDIRECT_URI`: Đường dẫn HTTPS (Ngrok Static Domain hoặc Domain Production).

---

## 5. Cổng Thanh Toán Tự Động VietQR & PayOS (Gói Thuê Bao)

Hệ thống xử lý thanh toán QR chuyển khoản ngân hàng tự động đối soát:

| Thông tin cấu hình | Biến môi trường | Nơi lấy / Đối soát |
| :--- | :--- | :--- |
| **PayOS Client ID** | `HAVI_PAYOS_CLIENT_ID` | [PayOS Dashboard](https://payos.vn/) |
| **PayOS API Key** | `HAVI_PAYOS_API_KEY` | PayOS $\rightarrow$ Quản lý Kênh thanh toán |
| **PayOS Checksum Key** | `HAVI_PAYOS_CHECKSUM_KEY` | Dùng để xác thực chữ ký Webhook thanh toán thành công |
| **Ngân hàng nhận tiền** | `HAVI_VIETQR_BANK_ID` | `MB` (Ngân hàng TMCP Quân Đội) |
| **Số tài khoản nhận tiền**| `HAVI_VIETQR_ACCOUNT_NO` | Số tài khoản ngân hàng của Founder |
| **Tên chủ tài khoản** | `HAVI_VIETQR_ACCOUNT_NAME` | Tên in hoa không dấu trên thẻ ngân hàng |

---

## 6. Hướng Dẫn Sao Lưu (Backup) & Khôi Phục Nhanh Khi Đổi Máy

Khi bạn chuyển sang máy tính mới hoặc cài lại máy, chỉ cần thực hiện 3 bước sau để chạy lại toàn bộ hệ thống trong 3 phút:

1. **Khôi phục file `.env`**:
   Sao chép toàn bộ nội dung file `.env` hiện tại vào thư mục gốc của dự án (`/havi/.env`) và thư mục backend (`/havi/apps/backend/.env`).

2. **Khởi động lại hạ tầng Docker**:
   ```bash
   docker-compose up -d
   ```

3. **Chạy Migration Database**:
   ```bash
   cd apps/backend
   alembic upgrade head
   ```
