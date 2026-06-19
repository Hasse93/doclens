"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import MatchResults from "@/components/MatchResults";
import StatusBadge from "@/components/StatusBadge";
import UploadCard from "@/components/UploadCard";
import { api, ApiError } from "@/lib/api";
import type { DocumentSummary, MatchResult } from "@/lib/types";

function DocList({
  title,
  docs,
  onDelete,
}: {
  title: string;
  docs: DocumentSummary[];
  onDelete: (id: number) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-700">{title}</h3>
      {docs.length === 0 ? (
        <p className="mt-2 text-xs text-slate-400">None yet.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {docs.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm shadow-sm ring-1 ring-slate-200"
            >
              <span className="min-w-0 truncate text-slate-700">{d.title}</span>
              <span className="ml-3 flex shrink-0 items-center gap-2">
                <StatusBadge status={d.status} />
                <button
                  onClick={() => onDelete(d.id)}
                  className="text-xs text-slate-400 transition hover:text-red-600"
                >
                  ✕
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function RecruitmentPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [jobId, setJobId] = useState<number | "">("");
  const [results, setResults] = useState<MatchResult[] | null>(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const all = await api.listDocuments();
    setDocs(all.filter((d) => d.mode === "recruitment"));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const jobs = useMemo(() => docs.filter((d) => d.role === "job"), [docs]);
  const resumes = useMemo(() => docs.filter((d) => d.role === "resume"), [docs]);

  // Poll while anything is still processing.
  useEffect(() => {
    const working = docs.some((d) => d.status === "pending" || d.status === "processing");
    if (working && !pollRef.current) {
      pollRef.current = setInterval(refresh, 2500);
    } else if (!working && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [docs, refresh]);

  async function handleDelete(id: number) {
    await api.deleteDocument(id);
    if (jobId === id) setJobId("");
    refresh();
  }

  async function runMatch() {
    if (jobId === "") return;
    setMatching(true);
    setError(null);
    setResults(null);
    try {
      const response = await api.match(Number(jobId));
      setResults(response.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Matching failed. Please try again.");
    } finally {
      setMatching(false);
    }
  }

  const readyJobs = jobs.filter((j) => j.status === "ready");
  const readyResumes = resumes.filter((r) => r.status === "ready");
  const canMatch = jobId !== "" && readyResumes.length > 0 && !matching;

  return (
    <AppShell>
      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <div className="space-y-6">
          <UploadCard
            mode="recruitment"
            role="job"
            heading="Job description"
            description="Upload the role's JD as a PDF."
            onUploaded={refresh}
          />
          <UploadCard
            mode="recruitment"
            role="resume"
            heading="Résumés"
            description="Upload one or more candidate résumés as PDFs."
            onUploaded={refresh}
          />
          <div className="space-y-4 rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-200">
            <DocList title="Job descriptions" docs={jobs} onDelete={handleDelete} />
            <DocList title="Résumés" docs={resumes} onDelete={handleDelete} />
          </div>
        </div>

        <section>
          <h2 className="text-lg font-semibold text-slate-900">Rank candidates</h2>
          <p className="mt-1 text-sm text-slate-500">
            Pick a job description, then score every ready résumé against it.
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <select
              value={jobId}
              onChange={(e) => setJobId(e.target.value ? Number(e.target.value) : "")}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            >
              <option value="">Select a job description…</option>
              {readyJobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
            <button
              onClick={runMatch}
              disabled={!canMatch}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {matching ? "Scoring…" : `Score ${readyResumes.length} résumé(s)`}
            </button>
          </div>

          {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

          {matching && (
            <p className="mt-6 text-sm text-slate-500">
              Scoring résumés against the job description…
            </p>
          )}

          {results && (
            <div className="mt-6">
              <MatchResults results={results} />
            </div>
          )}

          {!results && !matching && (
            <p className="mt-6 text-sm text-slate-400">
              Upload a job description and at least one résumé to get started.
            </p>
          )}
        </section>
      </div>
    </AppShell>
  );
}
