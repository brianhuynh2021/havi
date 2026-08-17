"use client";

/**
 * Route guard phía client cho 3 vùng: guest, cần onboarding, đã vào app.
 *
 * Đây là guard UX, không phải guard bảo mật — dữ liệu thật được bảo vệ ở backend
 * bằng JWT + tenant scope (api/deps.py). Người dùng sửa localStorage chỉ tự làm
 * mình thấy khung app rỗng rồi ăn 401, không đọc được gì của ai.
 */

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useSession } from "./session";

type Props = {
  /** "app" cần đã đăng nhập + đã onboarding; "onboarding" cần đã đăng nhập;
   * "guest" là màn đăng nhập/đăng ký, đã đăng nhập rồi thì không cần xem nữa. */
  require: "app" | "onboarding" | "guest";
  children: ReactNode;
};

export function RouteGuard({ require, children }: Props) {
  const router = useRouter();
  const { status, needsOnboarding } = useSession();

  useEffect(() => {
    if (require === "guest") {
      if (status === "authenticated") {
        router.replace(needsOnboarding ? "/onboarding" : "/app");
      }
      return;
    }

    if (status === "guest") {
      router.replace("/login");
      return;
    }

    if (require === "app" && needsOnboarding) {
      router.replace("/onboarding");
    }
  }, [status, needsOnboarding, require, router]);

  const redirecting =
    require === "guest"
      ? status === "authenticated"
      : status === "guest" || (require === "app" && needsOnboarding);

  if (redirecting) {
    return null;
  }

  return <>{children}</>;
}
