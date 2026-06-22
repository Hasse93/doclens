"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import StatusBadge from "@/components/StatusBadge";
import UploadCard from "@/components/UploadCard";
import { api } from "@/lib/api";
import type { DocumentSummary } from "@/lib/types";

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments());
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any document is still being processed, then stop.
  useEffect(() => {
    const stillWorking = documents.some(
      (d) => d.status === "pending" || d.status === "processing",
    );
    if (stillWorking && !pollRef.current) {
      pollRef.current = setInterval(refresh, 2500);
    } else if (!stillWorking && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents, refresh]);

  async function handleDelete(id: number) {
    await api.deleteDocument(id);
    refresh();
  }

  return (
    <AppShell>
      <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
        <UploadCard onUploaded={refresh} />

        <section>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Your documents</h2>

          {!loaded ? (
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Loading…</p>
          ) : documents.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
              No documents yet. Upload a PDF to get started.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {documents.map((doc) => (
                <li
                  key={doc.id}
                  className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200 dark:bg-slate-900 dark:ring-slate-800"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium text-slate-900 dark:text-slate-100">{doc.title}</p>
                      <StatusBadge status={doc.status} />
                    </div>
                    <p className="mt-0.5 truncate text-xs text-slate-400 dark:text-slate-500">
                      {doc.filename}
                      {doc.page_count > 0 && ` · ${doc.page_count} pages`}
                    </p>
                    {doc.status === "failed" && doc.error && (
                      <p className="mt-1 text-xs text-red-600">{doc.error}</p>
                    )}
                  </div>

                  <div className="ml-4 flex shrink-0 items-center gap-3">
                    {doc.status === "ready" && (
                      <Link
                        href={`/documents/${doc.id}`}
                        className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-brand-700"
                      >
                        Open
                      </Link>
                    )}
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="text-sm text-slate-400 transition hover:text-red-600"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </AppShell>
  );
}
