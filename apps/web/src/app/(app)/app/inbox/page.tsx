import { LeadsScreen } from "@/features/leads/leads-screen";

export const metadata = {
  title: "Hộp Thư — Havi",
};

export default function InboxPage() {
  return <LeadsScreen defaultTab="inbox" />;
}
