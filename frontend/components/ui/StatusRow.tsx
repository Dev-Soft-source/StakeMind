import { ScoreBadge } from "@/components/ui/ScoreBadge";

type StatusRowProps = {
  score: string | number;
  title: string;
  subtitle: string;
  active?: boolean;
};

export function StatusRow({ score, title, subtitle, active = false }: StatusRowProps) {
  return (
    <div
      className={[
        "flex items-center gap-4 rounded-xl border px-4 py-3 transition-colors",
        active
          ? "border-teal-500 bg-teal-500/5"
          : "border-slate-800/80 bg-slate-900/40 hover:border-slate-700",
      ].join(" ")}
    >
      <ScoreBadge value={score} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-slate-50">{title}</p>
        <p className="text-sm text-muted">{subtitle}</p>
      </div>
      <span
        className={[
          "h-3 w-3 rounded-full border",
          active ? "border-teal-400 bg-teal-400" : "border-slate-600 bg-transparent",
        ].join(" ")}
        aria-hidden="true"
      />
    </div>
  );
}
