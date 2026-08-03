import { AppShell } from "@/components/app-shell/app-shell";
import { DashboardScreen } from "@/features/dashboard/dashboard-screen";

export default function Home() {
  return (
    <AppShell>
      <DashboardScreen />
    </AppShell>
  );
}
