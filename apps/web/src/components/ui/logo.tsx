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
  /** Cạnh của logomark tính bằng px. */
  size?: number;
  /** `brand`, `dark`, hoặc `light` */
  tone?: "brand" | "dark" | "light";
  className?: string;
};

export function Logo({ size = 40, tone = "brand", className }: LogoProps) {
  const gradientId = `havi-grad-${size}`;
  const glowId = `havi-glow-${size}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="Havi"
      className={className}
      style={{ display: "block", flex: "none" }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#4F46E5" />
          <stop offset="50%" stopColor="#7C3AED" />
          <stop offset="100%" stopColor="#00D2FF" />
        </linearGradient>
        <linearGradient id={`${gradientId}-bg`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#111827" />
          <stop offset="100%" stopColor="#090D16" />
        </linearGradient>
        <filter id={glowId} x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#00D2FF" floodOpacity="0.35" />
        </filter>
      </defs>

      {/* Dark Premium Squircle Container */}
      <rect
        width="100"
        height="100"
        rx="26"
        fill={`url(#${gradientId}-bg)`}
        stroke="rgba(255, 255, 255, 0.12)"
        strokeWidth="1.5"
      />

      {/* Futuristic Ascending H with Velocity Arrow & AI Node */}
      <g filter={`url(#${glowId})`}>
        {/* Left Vertical Pillar */}
        <path
          d="M26 30 C26 26, 30 24, 34 26 L38 28 C41 30, 42 33, 40 37 L29 68 C28 72, 23 74, 20 72 L18 70 C15 67, 16 63, 18 59 Z"
          fill={`url(#${gradientId})`}
        />

        {/* Soaring Diagonal Growth Arch & Right Pillar */}
        <path
          d="M28 50 C38 48, 54 44, 62 34 L62 26 C62 22, 67 20, 71 23 L85 33 C88 35, 88 40, 84 43 L70 54 C66 57, 60 55, 60 50 L60 44 C53 50, 42 56, 30 58 Z"
          fill={`url(#${gradientId})`}
        />

        {/* Right Lower Stem */}
        <path
          d="M58 58 C62 55, 66 57, 67 61 L70 70 C72 74, 69 78, 64 78 L58 78 C54 78, 51 75, 52 71 Z"
          fill="#00D2FF"
        />

        {/* AI Hex Node Core */}
        <circle cx="56" cy="46" r="3.5" fill="#FFFFFF" />
        <circle cx="56" cy="46" r="6" stroke="#00D2FF" strokeWidth="1.5" fill="none" opacity="0.8" />
      </g>
    </svg>
  );
}

