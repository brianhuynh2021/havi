import type { ReactNode } from "react";
import { AuthShell } from "@/components/auth-shell/auth-shell";
import { RouteGuard } from "@/lib/auth/route-guard";

export default function AuthGroupLayout({ children }: { children: ReactNode }) {
  return (
    <RouteGuard require="guest">
      <AuthShell>{children}</AuthShell>
    </RouteGuard>
  );
}
