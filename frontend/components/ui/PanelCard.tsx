import type { ReactNode } from "react";

type PanelCardProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
};

export function PanelCard({ eyebrow, title, description, children }: PanelCardProps) {
  return (
    <section className="w-full rounded-2xl border border-slate-800/60 bg-surface p-6 shadow-lg shadow-black/20">
      {eyebrow ? <p className="text-sm font-medium text-accent">{eyebrow}</p> : null}
      <div className="mt-1 flex flex-col gap-2">
        <h2 className="text-xl font-semibold text-slate-50">{title}</h2>
        {description ? <p className="text-sm leading-6 text-muted">{description}</p> : null}
      </div>
      {children ? <div className="mt-5 space-y-3">{children}</div> : null}
    </section>
  );
}
