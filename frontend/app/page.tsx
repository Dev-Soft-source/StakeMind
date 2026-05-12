import { AppShell } from "@/components/layout/AppShell";
import { PlatformStatus } from "@/components/dashboard/PlatformStatus";

export default function Home() {
  return (
    <AppShell>
      <PlatformStatus />
    </AppShell>
  );
}