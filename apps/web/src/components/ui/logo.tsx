/**
 * Logomark Havi — chữ H dựng bằng ba thanh bo tròn, khoét một chấm ở cột phải.
 *
 * Thay cho chữ "Ha" cũ vì hai lý do:
 * 1. Lặp chữ — logomark "Ha" đứng cạnh wordmark "Havi" là nói hai lần một thứ.
 * 2. Không đọc được ở cỡ nhỏ. Ở 16px (favicon) hai ký tự bết thành vệt mờ;
 *    hình khối thì vẫn giữ được hình.
 *
 * Chấm khoét âm bản mang nghĩa "bài đã duyệt" — nguyên tắc review_first là thứ
 * Havi bán, nên nó xứng đáng nằm trong logo. Dùng khoét âm bản thay vì vẽ thêm
 * chi tiết màu khác: bớt một màu là bớt một thứ bết ở cỡ nhỏ.
 *
 * Mọi số đo nằm trên khung 40×40 rồi scale bằng `size` — sửa hình ở một chỗ,
 * mọi cỡ đổi theo, không bị lệch tỷ lệ giữa các màn.
 */

type LogoProps = {
  /** Cạnh của logomark tính bằng px. Nhỏ nhất nên dùng là 16. */
  size?: number;
  /** `dark` cho nền tối (footer): đảo màu nền/chữ. */
  tone?: "brand" | "dark";
  className?: string;
};

export function Logo({ size = 40, tone = "brand", className }: LogoProps) {
  const bg = tone === "dark" ? "#d4956f" : "var(--color-action)";
  const fg = tone === "dark" ? "#231f1c" : "#fff";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      role="img"
      aria-label="Havi"
      className={className}
      style={{ display: "block", flex: "none" }}
    >
      <rect width="40" height="40" rx="11.5" fill={bg} />
      <path
        d="M12.2 13a2.6 2.6 0 015.2 0v14a2.6 2.6 0 01-5.2 0zM22.6 13a2.6 2.6 0 015.2 0v14a2.6 2.6 0 01-5.2 0zM14.8 17.5h10.4a2.5 2.5 0 010 5H14.8a2.5 2.5 0 010-5z"
        fill={fg}
      />
      {/* Chấm khoét cùng màu nền, không phải màu thứ ba. */}
      <circle cx="25.2" cy="14.6" r="2.5" fill={bg} />
    </svg>
  );
}
