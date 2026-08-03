# Havi

> AI marketing đa ngành cho tiệm nhỏ & cá nhân kinh doanh — bán **kết quả**, không bán công cụ.

Havi là "nhân viên marketing AI" cho người dùng **không rành công nghệ** (spa, F&B, môi giới BĐS, kỹ sư/chuyên gia). Một luồng khép kín, chạy bằng 1 nút:

1. **Nạp liệu thô** (<30s) — ảnh chụp vội, ghi âm, vài dòng gõ tay, hoặc webhook từ phần mềm bán hàng
2. **Lò phản ứng AI** — tự nhận diện ngành → xử lý media → 1 lần gọi LLM sinh 4–5 bản nội dung theo kênh
3. **Tổng đài phân phối** — tự đăng đa kênh đúng khung giờ vàng qua API chính thức
4. **Săn mồi & chăm sóc** — social listening + soạn câu trả lời **chờ chủ duyệt** (không bao giờ tự gửi); CRM vòng đời khách + FAQ 24/7 (chỉ tự động với câu đã duyệt sẵn)

Mọi báo cáo đo bằng **khách hỏi giá / khách đến tiệm / khách quay lại** — không phải like/reach.

## Cấu trúc repo

| Thư mục | Nội dung |
|---|---|
| [`prototypes/`](prototypes/) | 6 prototype high-fidelity dạng `.dc.html` (mở trực tiếp trong trình duyệt) + `support.js` |
| [`docs/`](docs/) | Tài liệu được chia theo nhóm: handoff, product, architecture |

### Tài liệu chính

- [docs/README.md](docs/README.md) — index tài liệu theo từng nhóm
- [docs/handoff/HANDOFF.md](docs/handoff/HANDOFF.md) — mô tả chi tiết từng màn hình, fidelity, luồng duyệt bài
- [docs/product/ROADMAP.md](docs/product/ROADMAP.md) — lộ trình sản phẩm
- [docs/architecture/TECHNICAL_SPEC.md](docs/architecture/TECHNICAL_SPEC.md) — đặc tả kỹ thuật
- [docs/architecture/REPOSITORY_STRATEGY.md](docs/architecture/REPOSITORY_STRATEGY.md) — chiến lược tổ chức repo

### Prototype (`prototypes/`)

| File | Màn hình |
|---|---|
| `Havi - MVP App.dc.html` | Sản phẩm chính (sidebar + 5 tab) |
| `Havi - Onboarding.dc.html` | Onboarding 3 bước |
| `Havi - Đăng Nhập.dc.html` | Đăng nhập / Đăng ký |
| `Havi - Landing Page.dc.html` | Landing page |
| `Havi - AI Marketing.dc.html` | Trang giới thiệu AI marketing |
| `Havi - Kiến Trúc Hệ Thống.dc.html` | Sơ đồ kiến trúc hệ thống |

> Các file `.dc.html` là **design reference** thể hiện giao diện & hành vi mong muốn — không phải production code để copy. Nhiệm vụ: tái tạo pixel-perfect trong codebase thật.

## Tech stack (dự kiến)

- **Frontend:** Next.js
- **Backend:** FastAPI

## License

[MIT](LICENSE) © 2026 Huynh Nguyen
