import type { ReactNode } from "react";
import { AuthShell } from "@/components/auth-shell/auth-shell";

export default function AuthGroupLayout({ children }: { children: ReactNode }) {
  return <AuthShell>{children}</AuthShell>;
}
