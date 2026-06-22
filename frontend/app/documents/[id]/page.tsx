"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import ChatPanel from "@/components/ChatPanel";
import ExtractionPanel from "@/components/ExtractionPanel";
import NotesPanel from "@/components/NotesPanel";
import { BookOpen } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { DocumentSummary } from "@/lib/types";

export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);

  const [doc, setDoc] = useState<DocumentSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<null | "md" | "pdf">(null);

  async function exportReport(format: "md" | "pdf") {
    setExporting(format);
    try {
      const { filename, blob } = await api.fetchReport(documentId, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed.");
    } finally {
      setExporting(null);
    }
  }

  useEffect(() => {
    if (!Number.isFinite(documentId)) {
      setError("Invalid document.");
      return;
    }
    api
      .getDocument(documentId)
      .then(setDoc)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Could not load this document."),
      );
  }, [documentId]);

  return (
    <AppShell>
      <Link href="/dashboard" className="text-sm text-brand-600 hover:underline">
        ← Back to documents
      </Link>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {doc && (
        <>
          <header className="mt-3 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-slate-900">{doc.title}</h1>
              <p className="text-sm text-slate-400">
                {doc.filename}
                {doc.page_count > 0 && ` · ${doc.page_count} pages`}
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                onClick={() => exportReport("md")}
                disabled={exporting !== null}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
              >
                {exporting === "md" ? "Exporting…" : "Markdown"}
              </button>
              <button
                onClick={() => exportReport("pdf")}
                disabled={exporting !== null}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
              >
                {exporting === "pdf" ? "Exporting…" : "PDF"}
              </button>
            </div>
          </header>

          {doc.summary && (
            <div className="mt-5 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <h2 className="flex items-center gap-2 font-semibold text-slate-900">
                <BookOpen className="h-4 w-4 text-brand-600" />
                Summary
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{doc.summary}</p>
            </div>
          )}

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div className="lg:h-[560px]">
              <ChatPanel documentId={documentId} />
            </div>
            <div className="space-y-6">
              <ExtractionPanel documentId={documentId} />
              <NotesPanel documentId={documentId} />
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}
