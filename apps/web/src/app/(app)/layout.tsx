import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell/app-shell";
import { RouteGuard } from "@/lib/auth/route-guard";

export default function AppGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RouteGuard require="app">
      <AppShell>{children}</AppShell>
    </RouteGuard>
  );
}
