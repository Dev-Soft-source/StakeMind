import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen w-full bg-background text-foreground">
      <div className="flex min-h-screen w-full flex-col px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 w-full space-y-2 text-left">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-accent">StakeMind</p>
          <h1 className="text-3xl font-bold text-slate-50">Validator intelligence dashboard</h1>
          <p className="text-sm text-muted">
            Compare validators, review staking exposure, and track rewards from stored snapshots.
          </p>
        </header>
        <main className="flex w-full flex-1 flex-col gap-4">{children}</main>
      </div>
    </div>
  );
}
