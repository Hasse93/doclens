"use client";

import { useState } from "react";

import { ListChecks } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { ResearchExtraction } from "@/lib/types";

function Field({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-700 dark:text-slate-300">{value}</dd>
    </div>
  );
}

function ListField({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">{label}</dt>
      <dd className="mt-1">
        <ul className="list-inside list-disc space-y-0.5 text-sm text-slate-700 dark:text-slate-300">
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

export default function ExtractionPanel({ documentId }: { documentId: number }) {
  const [data, setData] = useState<ResearchExtraction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setData(await api.getExtraction(documentId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Extraction failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 dark:bg-slate-900 dark:ring-slate-800">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-slate-100">
          <ListChecks className="h-4 w-4 text-brand-600" />
          Structured data
        </h2>
        <button
          onClick={run}
          disabled={loading}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          {loading ? "Extracting…" : data ? "Re-extract" : "Extract"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {data && (
        <dl className="mt-4 space-y-4">
          <Field label="Title" value={data.title} />
          <ListField label="Authors" items={data.authors} />
          <Field label="Methodology" value={data.methodology} />
          <Field label="Dataset" value={data.dataset} />
          <ListField label="Key findings" items={data.key_findings} />
          <Field label="Limitations" value={data.limitations} />
        </dl>
      )}
    </div>
  );
}
