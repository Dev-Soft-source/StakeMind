import type { ReactNode } from "react";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-10 sm:px-8">
        <header className="mb-8 space-y-2 text-center sm:text-left">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-accent">StakeMind</p>
          <h1 className="text-3xl font-bold text-slate-50">Validator intelligence foundation</h1>
          <p className="text-sm text-muted">
            Phase 0 scaffold for analytics, wallet visibility, and staking intelligence.
          </p>
        </header>
        <main className="flex flex-1 flex-col gap-4">{children}</main>
      </div>
    </div>
  );
}
