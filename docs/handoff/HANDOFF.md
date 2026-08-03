# Handoff: Havi — AI Marketing Đa Ngành (MVP)

## Overview
Havi là "nhân viên marketing AI" cho tiệm nhỏ / cá nhân kinh doanh (spa, F&B, môi giới BĐS, kỹ sư/chuyên gia) — người dùng KHÔNG rành công nghệ. Luồng khép kín 4 trạm chạy bằng 1 nút:
1. **Nạp liệu thô** (<30s): ảnh chụp vội, ghi âm, vài dòng gõ tay, hoặc webhook từ phần mềm bán hàng
2. **Lò phản ứng AI**: tự nhận diện ngành → xử lý media → 1 lần gọi LLM sinh 4-5 bản nội dung theo kênh
3. **Tổng đài phân phối**: tự đăng đa kênh đúng khung giờ vàng (API chính thức)
4. **Săn mồi & chăm sóc**: social listening + soạn câu trả lời **chờ chủ duyệt** (không bao giờ tự gửi); CRM vòng đời khách (14/30 ngày) + FAQ trực 24/7 (chỉ tự động với câu chủ đã duyệt sẵn)

Bán kết quả, không bán công cụ: mọi báo cáo đo bằng **khách hỏi giá / khách đến tiệm / khách quay lại** — không phải like/reach.

## About the Design Files
Các file trong gói này là **design reference viết bằng HTML** (Design Component prototypes) — thể hiện giao diện và hành vi mong muốn, KHÔNG phải production code để copy. Nhiệm vụ: **tái tạo các thiết kế này trong môi trường codebase thật** bằng Next.js cho frontend và FastAPI cho backend. Mở từng file `.dc.html` trong trình duyệt để xem prototype chạy tương tác.

## Fidelity
**High-fidelity**: màu, chữ, khoảng cách, copy đều là bản cuối. Tái tạo pixel-perfect bằng thư viện/pattern của codebase.

## Screens / Views

### 1. MVP App (`Havi - MVP App.dc.html`) — SẢN PHẨM CHÍNH
Layout: sidebar trái cố định 232px (nền #2C2C2C) + main content (max-width 1080px, padding 28px 36px, nền #F5F1ED).

**Sidebar**: logo (ô 34px #D4956F, chữ "Ha" Merriweather 900) + nav 5 mục (Tổng quan, Tạo nội dung, Lịch đăng, Khách tiềm năng, Báo cáo — mục active nền rgba(212,149,111,.25), chữ trắng, badge đếm nền #D4956F) + thẻ workspace dưới cùng (tên tiệm + chip kênh đã nối, flex-wrap).

**Tab Tổng quan**:
- H1 chào theo buổi (Merriweather 900, 26px) + ngày
- 3 stat card bấm được (số Merriweather 900 26px màu #B8744D → điều hướng sang tab tương ứng)
- Ô nạp liệu: viền dashed 2px #D4956F, nút "+ Tạo nội dung mới"
- Khối tối #2C2C2C "Hôm nay chị bận? Havi vẫn có bài sẵn": 2 thẻ gợi ý (từ kho ảnh cũ / theo trend) với nút "Duyệt, đăng giúp tôi" → đổi thành pill xanh "Đã lên lịch · giờ"
- Banner Zalo: "Không cần mở app — duyệt ngay trong Zalo" + pill "Đã bật"
- Feed "Havi vừa làm gì cho chị": mỗi dòng = giờ (52px cột trái) + nội dung + tag pill (Nguyên liệu/Khách/Trực đêm/Chăm sóc/Đánh giá/Bài đăng/Maps)

**Tab Tạo nội dung**:
- Grid 360px + 1fr. Trái: danh sách liệu thô (chip loại: Ảnh/Ghi âm/Gõ tay màu #3B6B9F) + ô drop dashed + nút "Để Havi viết cho chị" + **toggle "Chế độ đăng bài"** (xem chi tiết Approval Workflow bên dưới)
- Bấm nút → trạng thái generating (3 câu status thay nhau ~900ms, animation pulse) → 2.9s ra 5 draft card
- **Thanh duyệt nhanh** (nền #2C2C2C, hiện khi còn bài pending): "{n} bài chờ chị xem qua" + nút "Duyệt & đăng hết" — 1 chạm approve toàn bộ
- Mỗi draft: chip kênh màu riêng (Fanpage #3B6B9F, Google Maps #5FA76F, Zalo #3B6B9F, Reels #B8744D, TikTok #2C2C2C) + loại bài + nút "Duyệt & lên lịch {giờ}" (duyệt lẻ từng bài) → pill "Đã lên lịch"; bài duyệt tự xuất hiện trên tab Lịch

**Tab Lịch đăng**: 4 cột ngày (hôm nay viền #D4956F nền trắng, ngày khác nền mờ); mỗi post card = chip kênh + giờ + 1 dòng mô tả

**Tab Khách tiềm năng**:
- Subtitle nêu nguyên tắc: "Không gì được gửi đi khi chị chưa duyệt"
- Strip "Trực tin nhắn 24/7 đang bật — 8 câu FAQ đã duyệt sẵn" (chấm xanh + pill Đã bật)
- Lead card: avatar chữ cái tròn 40px + tên + nguồn + status pill (Mới #D4956F / Cơ hội #3B6B9F / Đã trả lời ngay #5FA76F / Đang chăm sóc nền #F9EFE7 chữ #B8744D / Đã đặt lịch #5FA76F)
- Lead có reply: khung #F5F1ED "HAVI SOẠN SẴN — CHỊ DUYỆT RỒI MỚI GỬI" + nội dung + nút "Gửi trả lời này" → pill "Đã gửi"
- QUY TẮC COPY: câu seeding luôn minh bạch danh tính ("mình là chủ Spa An Nhiên...", "em là môi giới khu Q7...") — KHÔNG BAO GIỜ giả danh khách hàng

**Tab Báo cáo**:
- 3 stat card (▲ so tháng trước, chữ xanh #5FA76F)
- Khối "Khách đến tiệm từ kênh nào": 4 hàng, thanh ngang track #F0EAE4 / fill #D4956F + ghi chú nhỏ
- Bar chart 4 tuần (CSS bars, tuần nổi bật #B8744D)
- Khối tối "Havi nhận xét": 1 đoạn khuyên hành động bằng ngôn ngữ đời thường

### 2. Onboarding (`Havi - Onboarding.dc.html`)
3 bước, progress dots (active #D4956F, done #5FA76F + ✓):
1. Chọn ngành: grid 3×2 (Spa, Quán ăn/Cà phê, Môi giới, Kỹ sư, Shop online, Khác) — chọn thì viền + nền #F9EFE7; nút Tiếp tục disabled (#D9D1C9) khi chưa chọn
2. Nối kênh: 5 hàng (Facebook, Zalo, Maps, TikTok, YouTube) nút "Nối kênh" → pill "Đã nối"; cần ≥1
3. Learning state (~3s, 3 câu status) → "Bài đầu tiên đã sẵn sàng": Havi đọc bài cũ trên kênh để học giọng, hiện draft đầu tiên + CTA vào app

### 3. Đăng nhập / Đăng ký (`Havi - Đăng Nhập.dc.html`)
Card trắng 400px giữa màn (nền #F5F1ED), logo trên. Nguyên tắc: 1 màn = 1 việc, ít lựa chọn, chữ to (input 16-17px, padding 16px, radius 12px), nút chính full-width.
- **Đăng nhập (mặc định)**: 1 ô SĐT + nút "Nhận mã đăng nhập" (disabled #DCC9BB khi <9 số) → OTP. Phụ: nút "Tiếp tục với Zalo" (viền #3B6B9F); link nhỏ mở form email+mật khẩu.
- **Đăng ký**: chỉ tên + SĐT → OTP → dẫn vào Onboarding. Email/mật khẩu thêm sau trong Cài đặt.
- **OTP**: 6 ô 46×56px, tự nhảy ô, Backspace lùi ô, tự xác nhận khi đủ 6 số (demo: 111111), sai → viền đỏ #C0564A; đếm ngược 30s mới cho gửi lại.
- **Quên mật khẩu**: email → OTP → đặt mật khẩu mới.
- **Màn thành công**: check tròn #5FA76F; đăng nhập → MVP App, đăng ký → Onboarding.

### 4. Landing Page (`Havi - Landing Page.dc.html`)
Nav có link "Đăng nhập" + nút "Dùng thử miễn phí"; hero CTA "Dùng thử miễn phí 14 ngày" và nút bảng giá đều dẫn về trang Đăng Nhập. Hero (headline + 3 stat + khối tối "Bạn nạp vào ↓ Havi trả về") → 4 trạm → 3 thẻ ngành (Nạp/AI/Đăng/Săn) → Bảng giá 3 gói (0đ 14 ngày / Tiệm Nhỏ 299K / Toàn Diện 599K — gói 3 nền tối nổi bật) → CTA tối. KHÔNG lộ cơ chế nội bộ (chuỗi prompt, cách listening) — chỉ nói lợi ích.

### 5. Kiến trúc hệ thống (`Havi - Kiến Trúc Hệ Thống.dc.html`) — SPEC BACKEND, ĐỌC KỸ
Tài liệu nội bộ định hình backend. Tóm tắt bắt buộc:

**6 nguyên tắc**: (1) LLM chỉ chạy khi có lệnh/job rõ ràng, không loop nền; (2) lọc rẻ trước — keyword/rule → model nhỏ → LLM xịn; (3) 1 lần gọi sinh mọi kênh; (4) cache profile tenant (giọng, ngành, logo, giờ vàng) + prompt caching; (5) module hóa — lõi AI không biết kênh, mỗi kênh 1 adapter (ra nước mới = thêm adapter); (6) mọi việc là job có id qua hàng đợi, retry, ghi `event_log`.

**Kiến trúc**: Nguồn vào (app/web, webhook bán hàng, crawler listening) → Lõi (Ingest & Media Pipeline [code thường], Industry Profile Store [cache], Content Engine [LLM xịn], Listening Classifier [model rẻ], Reply Drafter + CRM [LLM xịn, luôn dừng ở PENDING_APPROVAL], Scheduler & Job Queue) → Adapters (FB/Zalo, TikTok/YouTube, Google Business, Zalo ZNS/Email).

**Phễu listening**: 100% bài → keyword+rule (0 token) → ~5% → model rẻ chấm điểm ý định → ~1% → LLM soạn trả lời → chờ duyệt.

**Vận hành**: `event_log` (tenant, job, input, output, tokens, time) — debug 1 dòng, tính tiền 1 query. Quota token/tháng theo gói; chạm trần thì xếp hàng.

## Repository & deployment
Xem `REPOSITORY_STRATEGY.md` (cùng thư mục): monorepo `havi-platform` với `apps/web` (Next.js) và `apps/backend` chứa FastAPI, Celery worker, scheduler và backend core; frontend chỉ gọi backend qua HTTP + OpenAPI client, không giữ secret nào; mỗi process deploy độc lập. Cấu trúc được chuẩn bị để sau này tách thành frontend, backend và infrastructure mà không copy thủ công.

## Approval Workflow (human-approval-first) — BẮT BUỘC
Nguyên tắc: **mặc định KHÔNG có nội dung nào lên mạng khi chủ chưa duyệt.**

**2 chế độ** (toggle trong tab Tạo nội dung, lưu theo tenant):
- `review_first` (mặc định, khuyên dùng): AI sinh draft → trạng thái `PENDING_APPROVAL` → chủ duyệt (lẻ từng bài hoặc "Duyệt & đăng hết") → `SCHEDULED` → worker đăng đúng giờ vàng → `PUBLISHED`
- `full_auto` (opt-in, chỉ nên mở khoá sau khi tenant đã duyệt ≥N bài với tỉ lệ sửa thấp): draft sinh xong tự chuyển `SCHEDULED` ngay; UI toggle #5FA76F khi bật

**State machine của 1 content item:**
`draft → pending_approval → approved → scheduled → publishing → published | failed (retry với backoff, max N lần → dead_letter)`
(full_auto chỉ bỏ qua bước pending_approval → approved; mọi trạng thái sau giữ nguyên)

**Quy tắc backend:**
- Duyệt là optimistic ở UI nhưng backend phải ghi `approved_by`, `approved_at` vào content item + audit log
- Idempotency key trên publish job — chống đăng đúp (user bấm 2 lần, 2 worker cùng lấy job): unique constraint + row lock
- Reply cho khách (lead/inbox) KHÔNG có chế độ full_auto — luôn `PENDING_APPROVAL`, trừ bộ FAQ chủ đã duyệt sẵn từng câu
- Version history: sửa draft tạo version mới, không ghi đè
- Phân loại lỗi publish: temporary (retry) / auth-permission (báo chủ nối lại kênh) / validation-permanent (không retry, hiện lý do)

## Interactions & Behavior
- Mọi state đổi qua click, không page reload (SPA)
- Generating/learning: chuỗi status message ~900ms/câu, tổng ~2.9s (prototype giả lập; bản thật = job async + polling/websocket)
- Duyệt = optimistic update (nút → pill xanh ngay), job gửi thật chạy nền
- Hover: nút primary #D4956F → #B8744D; card shadow 0 2px 8px → 0 8px 16px rgba(0,0,0,.12)
- Nút disabled: nền #D9D1C9
- KHÔNG có hành động gửi tự động nào ngoài: (a) đăng bài đã duyệt đúng lịch, (b) câu FAQ chủ đã duyệt sẵn

## State Management (bản thật)
- `tenant`: {industry, brandVoice(cached), logo, channels[], plan, tokenQuotaUsed}
- `content_job`: {id, tenantId, rawInputs[], status: queued|processing|drafts_ready, drafts[]}
- `draft`: {channel, kind, text, mediaNote, status: draft|pending_approval|approved|scheduled|publishing|published|failed, scheduledAt, approvedBy, approvedAt, versionHistory[]}
- `tenant.publishMode`: review_first (default) | full_auto — full_auto chỉ áp dụng cho content, KHÔNG áp dụng cho reply khách
- `auth`: SĐT+OTP là chính (qua Zalo/SMS); email+mật khẩu là phụ; đăng ký chỉ cần tên+SĐT, xác thực OTP
- `lead`: {source(fanpage|maps|group|crm), message, suggestedReply, status: new|auto_replied|awaiting_approval|sent|booked}
- `suggestion`: gợi ý tự động khi user không nạp gì (từ kho ảnh cũ / trend) — cùng vòng duyệt như draft
- A/B loop (bổ sung khi có dữ liệu): 2 biến thể tiêu đề/giờ đăng, so kết quả trong event_log, dồn về biến thể thắng

## Design Tokens
- Màu: primary #D4956F, primary-dark #B8744D, nền #F5F1ED, tối #2C2C2C, xám #4A4A4A, xám nhạt #8A817A, viền #E0D9D3, viền mảnh #F0EAE4, success #5FA76F, info #3B6B9F, alert/red #C75B4A, vàng #E8B84B, hover-nhạt #F9EFE7
- Chữ: Merriweather (700/900) cho display/heading; Inter (400-700) cho body/UI (Google Fonts)
- Spacing: lưới 8px (8/12/16/24/32/48); card padding 24px
- Radius: 8px chip/nút, 12px card, 999px pill; Shadow card: 0 2px 8px rgba(0,0,0,0.08)

## Assets
Không có asset ngoài — logo là ô vuông #D4956F chữ "Ha" (Merriweather 900). Font từ Google Fonts.

## Phase-1 build scope (khuyến nghị 4-6 tuần)
LÀM THẬT: nạp ảnh/gõ tay → Content Engine (1 gọi ra nhiều bài) → đăng qua API chính thức Facebook Fanpage + Google Business (Zalo OA sau) → duyệt qua Zalo OA → báo cáo tin nhắn hỏi giá/tuần + FAQ trực 24/7.
LÀM TAY SAU LƯNG (chưa code): listening (người thật lướt nhóm, dán vào hệ thống soạn trả lời), CRM vòng đời (lịch + template). Code crawler khi đã chứng minh ra khách.
LƯU Ý PHÁP LÝ: chỉ dùng API chính thức; mô hình duyệt-rồi-gửi là bắt buộc (điều khoản nền tảng + luật spam khi ra global).

## Files
- `Havi - MVP App.dc.html` — app chính (5 tab, tương tác đầy đủ)
- `Havi - Đăng Nhập.dc.html` — đăng nhập / đăng ký / OTP / quên mật khẩu
- `Havi - Onboarding.dc.html` — 3 bước onboarding
- `Havi - Landing Page.dc.html` — trang công khai + bảng giá
- `Havi - Kiến Trúc Hệ Thống.dc.html` — spec kiến trúc backend
- `Havi - AI Marketing.dc.html` — demo pitch 4 trạm (tham khảo flow, KHÔNG public)
</content>
