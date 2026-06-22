"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { DocumentSummary, MultiChatAnswer } from "@/lib/types";

export default function AskPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<MultiChatAnswer | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDocuments().then((all) =>
      setDocs(all.filter((d) => d.mode === "research" && d.status === "ready")),
    );
  }, []);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || asking) return;
    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      const ids = selected.size ? Array.from(selected) : undefined;
      setAnswer(await api.askAcrossDocuments(trimmed, ids));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't answer that. Please try again.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Ask across documents</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Search every research document at once, or narrow to a few. Answers cite the
        document and page they came from.
      </p>

      {docs.length === 0 ? (
        <p className="mt-6 text-sm text-slate-400 dark:text-slate-500">
          No ready research documents yet. Upload some on the Research tab first.
        </p>
      ) : (
        <>
          <div className="mt-6">
            <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
              Scope {selected.size > 0 ? `(${selected.size} selected)` : "(all documents)"}
            </p>
            <div className="flex flex-wrap gap-2">
              {docs.map((d) => {
                const on = selected.has(d.id);
                return (
                  <button
                    key={d.id}
                    onClick={() => toggle(d.id)}
                    className={`rounded-full px-3 py-1.5 text-sm ring-1 transition ${
                      on
                        ? "bg-brand-50 text-brand-700 ring-brand-300 dark:bg-brand-500/15 dark:text-brand-100 dark:ring-brand-500/40"
                        : "bg-white text-slate-600 ring-slate-200 hover:ring-slate-300 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700 dark:hover:ring-slate-600"
                    }`}
                  >
                    {on ? "✓ " : ""}
                    {d.title}
                  </button>
                );
              })}
            </div>
          </div>

          <form onSubmit={ask} className="mt-5 flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question across the selected documents…"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            <button
              type="submit"
              disabled={asking || !question.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {asking ? "Asking…" : "Ask"}
            </button>
          </form>

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

          {answer && (
            <div className="fade-up mt-6 space-y-4">
              <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 dark:bg-slate-900 dark:ring-slate-800">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800 dark:text-slate-200">
                  {answer.answer}
                </p>
              </div>

              {answer.citations.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Sources</p>
                  {answer.citations.map((c) => (
                    <div
                      key={c.marker}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-300"
                    >
                      <span className="font-semibold text-brand-700 dark:text-brand-300">
                        [{c.marker}] {c.document_title} · page {c.page_number}
                      </span>{" "}
                      — {c.snippet}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
