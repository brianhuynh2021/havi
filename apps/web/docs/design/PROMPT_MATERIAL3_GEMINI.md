# Prompt cho Gemini — Chuyển UI Havi sang tinh thần thiết kế Google (Material 3)

> Copy toàn bộ phần dưới dấu `---` và dán vào Gemini.

---

# NHIỆM VỤ

Bạn là chuyên gia Material Design 3 (Material You) của Google. Tôi có một web app tên **Havi** (Next.js 16 + React 19, **CSS Modules thuần, KHÔNG dùng Tailwind**). UI hiện tại theo phong cách "tech/neon": đầy gradient, glow xanh, nút nhấc lên khi hover. Tôi muốn nó mang **tinh thần thiết kế của Google: đơn giản nhưng tinh tế, gọn nhẹ, và khi chạm vào thì cảm giác thân thuộc, dễ gần**.

Hãy viết lại hệ thống thiết kế nền tảng theo Material 3.

---

## PHẦN 1 — BỐI CẢNH KỸ THUẬT (bắt buộc tôn trọng)

- **Framework**: Next.js 16 App Router, React 19, TypeScript.
- **Styling**: CSS Modules (`*.module.css`) + một file token toàn cục `src/app/globals.css`. **Tuyệt đối không đề xuất Tailwind, styled-components, MUI, hay bất kỳ thư viện CSS nào.** Chỉ CSS thuần + CSS custom properties.
- **Dark mode**: dùng `next-themes`, gắn class `.dark` lên phần tử gốc. Mọi token phải có giá trị cho **cả** `:root` (light) và `.dark`.
- **Không được đổi tên biến CSS đang tồn tại.** Codebase có ~40 file `.module.css` đang tham chiếu chúng. Bạn chỉ được **đổi giá trị** của biến cũ, và **thêm** biến mới. Nếu xoá/đổi tên biến, app sẽ vỡ.
- Ứng dụng có **thanh điều hướng bên trái nền tối** (sidebar `#020617`) trên desktop, và **bottom nav** trên mobile.
- Font hiện tại: `"Plus Jakarta Sans", "Inter", -apple-system, sans-serif`.
- Có visual regression test bằng Playwright → ưu tiên thay đổi **có hệ thống qua token**, hạn chế sửa lắt nhắt từng file.

---

## PHẦN 2 — HIỆN TRẠNG CẦN SỬA (số liệu thật từ codebase)

Tôi đã đếm trong `src/`:

| Vấn đề | Số lần xuất hiện | Vì sao trái tinh thần Google |
|---|---|---|
| `linear-gradient` / `radial-gradient` | **79** | Material 3 dùng **màu phẳng, đặc**. Gradient chỉ dành cho hình minh hoạ, không dùng cho nút/nav/badge. |
| Glow xanh `rgba(0, 102, 255, …)` | **90** | Google dùng bóng đổ **trung tính** (đen alpha thấp) để diễn tả độ cao, không dùng ánh sáng màu. |
| Glow cyan `rgba(0, 210, 255, …)` | **68** | Như trên. Neon là ngôn ngữ gaming/crypto, không phải Google. |
| `transform: translateY(-1px)` khi hover | **44** | Google **không nhấc phần tử lên**. Phản hồi chạm được thể hiện bằng **state layer** (lớp phủ mờ) đổi độ đậm. |

Ngoài ra:
- Bo góc đang là 12px đồng loạt → Material 3 dùng **thang shape phân cấp**, nút thường là **full-round**.
- **Chưa hề có ripple** — đây chính là thứ tạo cảm giác "chạm vào thấy thân thuộc" mà tôi muốn.
- Easing đang là `cubic-bezier(0.16, 1, 0.3, 1)` (kiểu iOS) → Material 3 dùng bộ easing riêng.

---

## PHẦN 3 — NGUYÊN TẮC MATERIAL 3 CẦN ÁP DỤNG

### 3.1 State layer (QUAN TRỌNG NHẤT — đây là "cảm giác chạm" của Google)
Mọi phần tử tương tác được phủ một lớp màu `on-*` với độ mờ thay đổi theo trạng thái. **Không đổi kích thước, không dịch chuyển, không đổi bóng khi hover.**

| Trạng thái | Opacity của state layer |
|---|---|
| Enabled (mặc định) | 0% |
| Hover | **8%** |
| Focus | **10%** |
| Pressed | **10%** |
| Dragged | 16% |

Triển khai bằng pseudo-element `::before` phủ kín (`position:absolute; inset:0`), `background: currentColor`, `opacity` đổi theo state, `pointer-events:none`. Phần tử cha cần `position:relative; overflow:hidden; isolation:isolate`.

### 3.2 Ripple (hiệu ứng lan từ điểm chạm)
Đây là chi tiết khiến UI Google "dễ gần". Yêu cầu:
- Ripple lan **từ đúng toạ độ ngón tay/con trỏ chạm**, không phải từ tâm.
- Thời lượng ~**400–550ms**, easing `cubic-bezier(0.2, 0, 0, 1)`.
- Màu = `currentColor` với opacity ~0.12, mờ dần về 0.
- **Bắt buộc tôn trọng `@media (prefers-reduced-motion: reduce)`** → tắt ripple, chỉ giữ state layer.
- Viết bằng **React hook thuần + CSS**, KHÔNG dùng thư viện.

### 3.3 Motion (nhịp chuyển động)
Dùng đúng bộ easing/duration của Material 3:

```
--m3-easing-standard: cubic-bezier(0.2, 0, 0, 1);
--m3-easing-emphasized: cubic-bezier(0.2, 0, 0, 1);
--m3-easing-decelerate: cubic-bezier(0, 0, 0, 1);
--m3-easing-accelerate: cubic-bezier(0.3, 0, 1, 1);

--m3-duration-short:  100ms;  /* state layer, ripple bắt đầu */
--m3-duration-medium: 200ms;  /* đa số chuyển tiếp */
--m3-duration-long:   400ms;  /* sheet, dialog, chuyển trang */
```
Nguyên tắc: **phần tử vào màn hình thì decelerate, rời màn hình thì accelerate.**

### 3.4 Shape (thang bo góc)
```
--m3-shape-xs:    4px;
--m3-shape-sm:    8px;
--m3-shape-md:   12px;
--m3-shape-lg:   16px;
--m3-shape-xl:   28px;
--m3-shape-full: 999px;
```
Áp dụng: **Button → full (999px)**. Card → lg (16px). Input/text field → xs trên, bo góc dưới vuông (kiểu filled) HOẶC sm nếu dùng outlined. Dialog → xl (28px). FAB → lg. Chip → sm.

### 3.5 Elevation (bóng đổ trung tính, KHÔNG màu)
```
--m3-elevation-0: none;
--m3-elevation-1: 0 1px 2px rgba(0,0,0,.30), 0 1px 3px 1px rgba(0,0,0,.15);
--m3-elevation-2: 0 1px 2px rgba(0,0,0,.30), 0 2px 6px 2px rgba(0,0,0,.15);
--m3-elevation-3: 0 4px 8px 3px rgba(0,0,0,.15), 0 1px 3px rgba(0,0,0,.30);
```
Ở dark mode, Material 3 **không tăng bóng mà tăng độ sáng bề mặt** (surface tint). Hãy làm đúng vậy.

### 3.6 Typography
Giữ font `Plus Jakarta Sans` nhưng dựng **type scale** kiểu Material 3, và **giảm độ đậm**: hiện tại nhiều chỗ dùng `font-weight: 700–800`, Google thường dùng **400 cho body, 500 (medium) cho label/nút, 400 cho headline**. Chữ nút Google là `500`, KHÔNG phải `700`.
Cần các bậc: `display-*`, `headline-*`, `title-*`, `body-*`, `label-*`.

---

## PHẦN 4 — BẢNG MÀU

Giữ nguyên màu thương hiệu **`#0066ff`** làm màu primary (đây là nhận diện của Havi, tôi không muốn đổi thành xanh Google `#0b57d0`). Nhưng hãy **dựng đầy đủ bộ vai trò màu (color roles) của Material 3** xoay quanh nó bằng thuật toán tonal palette:

Cần sinh đủ các vai trò cho **cả light và dark**:
```
primary, on-primary, primary-container, on-primary-container,
secondary, on-secondary, secondary-container, on-secondary-container,
tertiary, on-tertiary, tertiary-container, on-tertiary-container,
error, on-error, error-container, on-error-container,
surface, on-surface, surface-variant, on-surface-variant,
surface-container-lowest / low / (base) / high / highest,
outline, outline-variant, inverse-surface, on-inverse-surface, scrim
```

Ràng buộc:
- Mọi cặp `on-X` trên `X` phải đạt **tương phản ≥ 4.5:1** (WCAG AA). Hãy tự kiểm tra và ghi rõ tỉ số tương phản cho các cặp chính.
- **Hạ độ bão hoà nền**: nền hiện tại `#f1f3f8` hơi xanh → Material 3 dùng nền gần trung tính, ám rất nhẹ màu primary.
- Dark mode surface hiện là `#090d16` (gần đen tuyệt đối) → Material 3 dùng `#131318`-ish, **không bao giờ đen tuyền**, và các lớp container sáng dần theo độ cao.
- **Xoá hoàn toàn** `--shadow-glow`, `--shadow-cyan-glow`, `--color-accent-cyan` khỏi vai trò UI (giữ biến để không vỡ build, nhưng gán về giá trị trung tính/none).

---

## PHẦN 5 — SẢN PHẨM CẦN GIAO

Hãy trả về code hoàn chỉnh, dán được ngay, cho các mục sau:

**1. `src/app/globals.css` (viết lại phần token)**
- Toàn bộ color roles M3 cho `:root` và `.dark`.
- Token motion, shape, elevation, typography.
- **Giữ lại và ánh xạ mọi biến cũ** sang vai trò M3 mới. Danh sách biến cũ **bắt buộc phải còn tồn tại**:
  `--color-bg, --color-surface, --color-surface-glass, --color-primary, --color-primary-dark, --color-primary-light, --color-action, --color-action-hover, --color-action-disabled, --color-placeholder, --color-ink, --color-body, --color-muted, --color-border, --color-border-soft, --color-border-glow, --color-success, --color-danger, --color-info, --badge-success-text, --badge-info-text, --badge-warning-text, --glow-top, --glow-side, --shadow-card, --shadow-card-hover, --shadow-glow, --shadow-cyan-glow, --font-body, --font-display, --color-background, --color-paper, --color-surface-dark, --color-surface-darker, --bg-surface, --bg-canvas, --border-color, --text-primary, --text-secondary, --text-on-dark, --text-on-dark-soft, --color-brand-primary, --color-brand-primary-light, --color-brand-primary-dark, --color-brand-action, --color-brand-primary-text, --color-primary-text`
  cùng toàn bộ thang màu primitive `--color-slate-*, --color-red-*, --color-orange-*, --color-amber-*, --color-green-*, --color-emerald-*, --color-blue-*, --color-indigo-*, --color-purple-*, --color-fuchsia-*, --color-pink-*, --color-white, --color-black, --color-transparent`.
  → Cách làm: định nghĩa token M3 mới trước, rồi khai báo biến cũ như alias trỏ vào token mới. Ví dụ `--color-border: var(--m3-outline-variant);`
- Bỏ 2 lớp `radial-gradient` glow trên `body`, thay bằng nền phẳng `var(--m3-surface)`.

**2. `src/components/ui/ripple.tsx` + `ripple.module.css`** (component/hook mới)
- Hook `useRipple()` trả về ref + handler, hoặc component `<Ripple />` đặt bên trong nút.
- Ripple lan từ toạ độ chạm thật, hỗ trợ cả `pointerdown` (chuột + cảm ứng) và bàn phím (khi focus + Enter/Space thì lan từ tâm).
- Tôn trọng `prefers-reduced-motion`.
- Dọn dẹp DOM node sau khi animation kết thúc để không rò rỉ.

**3. `src/components/ui/button.module.css` (viết lại)**
Giữ nguyên tên các class hiện có: `.button, .primary, .ghost, .outline, .large`. Ánh xạ sang các kiểu nút Material 3:
- `.primary` → **Filled button**: nền `primary` phẳng (BỎ gradient), chữ `on-primary`, bo `full`, `elevation-0`, hover thêm state layer 8% + `elevation-1`.
- `.outline` → **Outlined button**: nền trong suốt, viền 1px `outline`, chữ `primary`.
- `.ghost` → **Text button**: không nền, không viền, chữ `primary`, padding ngang 12px.
- `.large` → giữ full-width, chiều cao 40–56px theo M3.
- **BỎ HẾT** `translateY(-1px)` và mọi `box-shadow` màu xanh.
- Chiều cao chuẩn M3 là **40px**; hiện tại `min-height: 48px`. Hãy giữ **48px** vì đây là app dùng nhiều trên mobile và 48px là kích thước chạm tối thiểu của chính Google (Material touch target). Giải thích rõ lựa chọn này.

**4. `src/components/ui/button.tsx` (cập nhật)** — gắn ripple vào, giữ nguyên API props `variant` / `scale` / `className` để không phải sửa nơi gọi.

**5. `src/components/ui/card.module.css`** → surface phẳng, `elevation-1`, bo `lg`, viền `outline-variant`. Nếu card bấm được thì thêm state layer.

**6. `src/components/ui/input.module.css`** → dựng lại theo **Material 3 filled text field**: nền `surface-container-highest`, gạch chân dày 1px (2px khi focus, màu `primary`), bo góc trên `xs` và góc dưới vuông. Bỏ `box-shadow` glow cyan. Lưu ý class `.large` hiện đang hardcode nền tối `#0f172a` cho màn đăng nhập — hãy xử lý bằng token thay vì hardcode.

**7. `src/components/ui/badge.module.css`** → dùng cặp `*-container` / `on-*-container` của M3 thay cho `rgba()` tự chế.

**8. `src/components/app-shell/app-shell.module.css`** → 
- Sidebar theo kiểu **Navigation Drawer** của M3: mục active có **pill bo tròn full** nền `secondary-container`, chữ `on-secondary-container`, **KHÔNG gradient, KHÔNG glow**.
- Bottom nav mobile theo **Navigation Bar** M3: **indicator hình viên thuốc bo tròn ôm lấy icon** (đây là chi tiết đặc trưng nhất của Material 3), label 12px weight 500 ở dưới.
- Bỏ `transform: scale(1.12)` trên icon active, thay bằng indicator pill.

**9. Bảng đối chiếu "trước → sau"** liệt kê từng quyết định: bỏ cái gì, thay bằng gì, lý do theo nguyên tắc Material 3 nào.

---

## PHẦN 6 — RÀNG BUỘC CUỐI

- **Không đổi cấu trúc JSX/DOM** trừ khi bắt buộc (ví dụ thêm `<span>` cho ripple) — và nếu có thì phải nói rõ.
- **Không xoá biến CSS nào.**
- Mọi thứ phải chạy được ở **cả light và dark mode**.
- Đảm bảo focus ring nhìn thấy rõ cho bàn phím (`:focus-visible`), đây là yêu cầu accessibility của Google.
- Kích thước chạm tối thiểu **48×48px**.
- Viết chú thích trong CSS bằng **tiếng Việt**, ngắn gọn, giải thích *tại sao* chứ không phải *cái gì*.
- Trả code trong các khối code riêng biệt, ghi rõ đường dẫn file trên mỗi khối.

---

## PHẦN 7 — TỰ KIỂM TRA TRƯỚC KHI TRẢ LỜI

Xác nhận từng điểm:
- [ ] Không còn `linear-gradient` / `radial-gradient` nào trong nút, nav, badge, card.
- [ ] Không còn `box-shadow` mang màu xanh/cyan.
- [ ] Không còn `translateY` khi hover.
- [ ] Mọi biến CSS cũ trong danh sách ở Phần 5.1 vẫn tồn tại.
- [ ] Có state layer 8% hover / 10% focus / 10% pressed.
- [ ] Có ripple lan từ điểm chạm và tôn trọng `prefers-reduced-motion`.
- [ ] Mọi cặp `on-X` trên `X` đạt tương phản ≥ 4.5:1, có ghi số cụ thể.
- [ ] Có đủ token cho `.dark`.
