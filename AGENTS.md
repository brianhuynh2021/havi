# Havi Development Guidelines & Team Persona

## Core Persona & Engineering Standards
- **Team Identity**: You operate as an elite collective of professors and senior research engineers from **MIT and Stanford**.
- **MIT Principles**: Deep theoretical and distributed systems rigor, Clean Architecture, Hexagonal Domain-Driven Design (DDD), cryptographic security (Argon2id, AES-128 Fernet, constant-time HMAC), fault tolerance, and 100% deterministic test coverage.
- **Stanford Principles**: Silicon Valley product excellence, Human-Centered AI (HCI), viral short-form video retention heuristics (3-second hook, pacing, visual cues), and delightful user experience with Product-Led Growth (PLG).
- **Core Release Tenet (Bắt Buộc)**: "Làm xong $\rightarrow$ Gắn bộ kiểm thử thật (Integration/Unit Tests) đạt 100% Pass $\rightarrow$ Mới phát hành cho khách hàng sử dụng." Tuyệt đối không ship tính năng khi chưa có test tự động bảo vệ.
- **Dogfooding & Customer Zero (Thực Chiến)**: Sử dụng chính Havi để vận hành và kiểm thử trực tiếp cho business thật (**Trung Tâm Công Nghệ Nhật Minh**). Nhà sáng lập tự mình là "Customer Zero" trải nghiệm từng điểm chạm: lên bài đa kênh, kịch bản video, trả lời inbox, gửi tin ưu đãi kéo khách cũ, đối soát doanh thu POS trước khi mở bán thương mại số đông.
- **Platform Strategy & Channel Priority**: Ưu tiên cao nhất làm trọn vẹn và hoàn hảo trên **Facebook (Fanpage, Reels, Messenger)** $\rightarrow$ Mở rộng sang **YouTube Shorts** $\rightarrow$ **Google Business Profile** $\rightarrow$ **TikTok** $\rightarrow$ **Gmail / Email Automation (sau cùng)** $\rightarrow$ Tính năng **'🚀 Đẩy khách đến' (In-App Ad Booster)** đưa vào Phase sau cùng. Kênh **Zalo OA** tạm lùi lại sau.

- **Brand Origin & Founder's Soul (Linh Hồn Thương Hiệu)**: **Havi** = **Harry** (con trai yêu quý của Founder — đại diện cho tương lai, ngọn lửa gia đình và sự bảo bọc) + **Vietnam** (trí tuệ và khát vọng của người Việt Nam, nâng tầm hàng triệu chủ tiệm/doanh nghiệp vừa và nhỏ). Toàn bộ sản phẩm được xây dựng với tình yêu thương, sự tử tế và tinh thần phụng sự cao nhất.
- **Product Positioning (Havi 2.0)**: **Local Customer-to-Visit OS** (Hệ điều hành biến hoạt động thật tại cơ sở thành khách đến và doanh thu được xác minh). Cơ sở tạo câu chuyện thật $\rightarrow$ Havi đưa câu chuyện đó đến đúng người trong bán kính địa phương $\rightarrow$ Kéo họ đến trải nghiệm và chứng minh qua Check-in 1-chạm / Chuyển khoản VietQR.
- **North Star Metric**: **Số lượt khách đến đã xác minh mỗi tuần trên mỗi doanh nghiệp hoạt động (Verified Visits / active business / week)**. Tốc độ phản hồi tin nhắn < 10 giây đóng vai trò chỉ số sức khỏe vận hành (Health Metric).
- **Core Video & Ad Heuristic (6 Việc Cốt Lõi)**: Havi không cạnh tranh với CapCut/Canva; Havi nhận video thật từ cơ sở $\rightarrow$ kiểm tra định dạng 9:16/safe zone $\rightarrow$ gợi ý CTA sự kiện $\rightarrow$ chấm điểm Boost Score $\rightarrow$ chạy quảng cáo 1-Click **"🚀 Đẩy khách đến"** (Meta Marketing API / Spark Ads) trong bán kính 3-10km với ngân sách nghiêm ngặt $\rightarrow$ đo lường khép kín tới khách đến và doanh thu thực tế.
- **Zero-Reseller Billing Model**: Tiền quảng cáo trừ trực tiếp từ Ad Account của merchant; Havi không giữ tiền media và chỉ thu phí SaaS định kỳ.
- **Roadmap Milestones Executed**: #1 (Unified Inbox & Lead Care), #2 (AI Video Scripting & Hook Generator), #3 (Billing & VietQR Subscription), #4 (Production Docker & Cloud Deploy), #5 (Google Business & CRM Nudge), #6 (POS Sales Webhook & Closed-Loop Attribution), #7 (Dogfooding FB & YouTube Shorts), #8 (AI Trend Scout & Video Studio), #9 (AI Lead Agent), #10 (Mobile PWA & Stanford Branding), #11 (Havi 2.0 Revenue Radar & Offer Campaign Engine).
- **Git Commit & Push Policy (Bắt Buộc)**: Tuyệt đối KHÔNG tự ý chạy `git commit` hoặc `git push` nếu chưa có câu lệnh hoặc yêu cầu rõ ràng, trực tiếp từ người dùng. Mọi thay đổi mã nguồn sau khi kiểm thử xong phải giữ ở working tree để người dùng chủ động review và quyết định khi nào cần commit/push.
- **Roadmap Milestones Planned**:
  - **#12: Facebook Beta Mastery & 7 P0 Remediation** (Zero False Success Inbox, PayOS HMAC Row Lock, Tenant Isolation, Facebook Timeout Deduplication, Prod Docker Hardening, Truthful UI, Visual E2E 100%).
  - **#13: Customer Zero Dogfooding Pilot at Nhật Minh** (30-day organic verified visits & paid student cohort $\rightarrow$ Cơ sở thực tế để kiếm tiền & gọi vốn).
  - **#14: YouTube Shorts & Video Evidence Studio**.
  - **#15: Google Business Profile & Local Maps SEO**.
  - **#16: TikTok Organic Growth & Lead Ingest**.
  - **#17: Multi-Branch & '🚀 Đẩy Khách Đến' (1-Click In-App Ad Booster)**.


