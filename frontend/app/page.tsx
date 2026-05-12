import { Dashboard } from "@/components/dashboard/Dashboard";
import { AppShell } from "@/components/layout/AppShell";

export default function Home() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
