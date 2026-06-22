import type { MatchResult } from "@/lib/types";

function scoreColor(score: number): string {
  if (score >= 75) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function Chips({ items, tone }: { items: string[]; tone: "good" | "bad" }) {
  if (!items.length) return <span className="text-xs text-slate-400">—</span>;
  const cls =
    tone === "good"
      ? "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/30"
      : "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-500/30";
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span key={i} className={`rounded-full px-2 py-0.5 text-xs ring-1 ${cls}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

export default function MatchResults({ results }: { results: MatchResult[] }) {
  if (!results.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No résumés were scored.</p>;
  }

  return (
    <ol className="space-y-4">
      {results.map((r, index) => (
        <li
          key={r.resume_id}
          className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 dark:bg-slate-900 dark:ring-slate-800"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-slate-100 text-sm font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {index + 1}
              </span>
              <h3 className="font-medium text-slate-900 dark:text-slate-100">{r.resume_title}</h3>
            </div>
            <div className="text-right">
              <span className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{r.score}</span>
              <span className="text-sm text-slate-400 dark:text-slate-500">/100</span>
            </div>
          </div>

          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div
              className={`h-full ${scoreColor(r.score)}`}
              style={{ width: `${r.score}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            Semantic similarity {r.semantic_score}/100
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                Matched
              </p>
              <Chips items={r.matched_skills} tone="good" />
            </div>
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                Missing
              </p>
              <Chips items={r.missing_skills} tone="bad" />
            </div>
          </div>

          {r.recommendation && (
            <p className="mt-4 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{r.recommendation}</p>
          )}
        </li>
      ))}
    </ol>
  );
}
