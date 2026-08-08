import type { ReactNode } from "react";
import { RouteGuard } from "@/lib/auth/route-guard";

/** Onboarding chỉ cần đã đăng nhập — chưa có workspace là chuyện bình thường ở
 * đây, nên không dùng `require="app"` (sẽ đá vòng về chính /onboarding). */
export default function OnboardingGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <RouteGuard require="onboarding">{children}</RouteGuard>;
}
