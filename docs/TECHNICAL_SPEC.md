# Technical Spec — Modules còn thiếu so với PRD gốc

Bổ sung cho README.md + REPOSITORY_STRATEGY.md. Backend = FastAPI (`apps/backend/api`), owner mọi DB/secret.

## 1. Workspace (multi-tenant)
- `workspace {id, name, industry, owner_user_id, plan, created_at}`
- `workspace_member {workspace_id, user_id, role: owner|marketer|reviewer|sales}`
- 1 user có thể thuộc nhiều workspace; JWT mang `active_workspace_id`; mọi query API scope theo workspace_id (row-level, không cho leak chéo tenant)
- UI: màn "Chọn tiệm" sau login nếu user có >1 workspace

## 2. Brand Profile / Brand Voice
- `brand_profile {workspace_id, industry, tone, banned_claims[], faq[], logo_url, brand_colors[]}`
- Là input bắt buộc cho mọi prompt chế bản (worker đọc từ đây, không hardcode)
- UI: form trong Settings — giọng văn (vui/trang trọng/thân thiện), danh sách từ/khẳng định cấm dùng (vd BĐS: "chắc chắn tăng giá"), FAQ trả lời sẵn

## 3. Media Library
- `media_asset {id, workspace_id, url, type: image|audio|video, tags[], status: raw|used|archived, uploaded_at}`
- Upload trực tiếp lên object storage (S3-compatible), API chỉ lưu metadata
- UI: lưới ảnh/audio đã nạp, filter theo tag/trạng thái, tái sử dụng cho bài mới

## 4. Content Calendar
- `content_item.scheduled_at` là nguồn dữ liệu; calendar là view, không phải bảng riêng
- UI: lịch tháng/tuần, click ô xem bài đã lên lịch theo kênh (màu theo kênh, giống chip trong MVP App), kéo-thả đổi giờ đăng (chỉ cho item ở trạng thái `approved`/`scheduled`, không cho sửa `published`)

## 5. Content Editor & Approval Queue (tách riêng khỏi tab "Tạo nội dung")
- Đã có approval bar trong MVP App; bổ sung màn **Hàng chờ duyệt** riêng: danh sách tất cả `pending_approval` xuyên workspace, filter theo kênh/ngày, bulk approve/reject, mở sửa text trước khi duyệt
- `content_item_version {content_item_id, version_no, text, edited_by, edited_at}` — mỗi lần sửa tạo version mới

## 6. Connected Accounts
- `platform_connection {workspace_id, platform: facebook|google_business|zalo_oa, access_token_encrypted, refresh_token_encrypted, expires_at, status: connected|expired|revoked, connected_by}`
- Token mã hoá bằng `TOKEN_ENCRYPTION_KEY` (backend only), OAuth flow chuẩn từng nền tảng, refresh job trong scheduler
- UI: danh sách nền tảng, trạng thái (chấm xanh/đỏ), nút "Kết nối lại" khi expired — không tự đăng được khi status != connected

## 7. Unified Inbox
- `inbox_item {id, workspace_id, platform, type: comment|review|message, content, author_name, sentiment, ai_suggested_reply, status: new|drafted|sent, created_at}`
- Social listening (worker, polling API chính thức) → tạo `inbox_item` + AI soạn `ai_suggested_reply` (luôn xưng danh chủ tiệm/môi giới, không giả danh khách)
- Reply KHÔNG có full_auto — luôn cần bấm gửi (đúng triết lý Havi)
- UI: 1 luồng chat gộp mọi nền tảng, mỗi item có nút "Gửi", "Sửa rồi gửi", "Bỏ qua"

## 8. Lead Pipeline (CRM)
- `lead {id, workspace_id, name, phone, source, stage: new|contacted|qualified|won|lost, notes, created_at}`
- `crm_message {lead_id, channel: zalo|email, draft_text, status: pending_approval|sent, created_at}` — AI soạn tin nuôi khách, chủ duyệt từng tin
- UI: kanban theo stage, kéo-thả đổi stage, mỗi lead có lịch sử tin nhắn

## 9. Analytics Dashboard
- Nguồn: `content_item.published_at/engagement_snapshot` (polling API nền tảng theo lịch) + `lead` conversion
- Chỉ số tối thiểu: bài đã đăng theo kênh, tổng tương tác, lead mới, tỉ lệ lead→won
- UI: dashboard riêng, biểu đồ theo tuần/tháng, không cần real-time

## 10. Settings & Billing
- Brand profile (mục 2), Connected accounts (mục 6), Chế độ đăng bài (review_first/full_auto, đã có trong MVP App)
- `subscription {workspace_id, plan, status, current_period_end}` — tích hợp cổng thanh toán VN (VNPay/Momo) qua backend, không lộ secret ra frontend
- Quản lý thành viên workspace (mời, đổi role, xoá)

## API surface (OpenAPI, tóm tắt theo domain)
```
/auth/*              OTP, email login, refresh token
/workspaces/*         CRUD, members
/brand-profile        GET/PUT
/media                upload, list, tag
/content              CRUD, /content/{id}/approve, /content/{id}/versions
/calendar             GET (view over content)
/connections/*        OAuth start/callback, status, disconnect
/inbox                list, /inbox/{id}/reply
/leads                CRUD, kanban stage update
/crm-messages         list, approve/send
/analytics            summary, timeseries
/billing              plan, invoices
```
Mọi endpoint yêu cầu `Authorization: Bearer <JWT>` + scope theo `active_workspace_id`.
