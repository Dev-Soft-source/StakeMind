type ScoreBadgeProps = {
  value: string | number;
};

export function ScoreBadge({ value }: ScoreBadgeProps) {
  return (
    <span className="inline-flex min-w-10 items-center justify-center rounded-md bg-teal-700 px-3 py-1 text-sm font-bold text-white">
      {value}
    </span>
  );
}
