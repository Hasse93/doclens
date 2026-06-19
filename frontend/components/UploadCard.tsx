"use client";

import { useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";

interface UploadCardProps {
  onUploaded: () => void;
  mode?: string;
  role?: string;
  heading?: string;
  description?: string;
}

export default function UploadCard({
  onUploaded,
  mode = "research",
  role = "document",
  heading = "Upload a document",
  description = "PDF only. We extract the text, build a searchable index, and write a summary.",
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  function pickFile(selected: File | null) {
    setError(null);
    if (selected && selected.type !== "application/pdf") {
      setError("Please choose a PDF file.");
      return;
    }
    setFile(selected);
    if (selected && !title) setTitle(selected.name.replace(/\.pdf$/i, ""));
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(file, title.trim() || file.name, mode, role);
      setFile(null);
      setTitle("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h2 className="text-lg font-semibold text-slate-900">{heading}</h2>
      <p className="mt-1 text-sm text-slate-500">{description}</p>

      <div className="mt-4 space-y-3">
        <label
          htmlFor={`file-${mode}-${role}`}
          className="flex cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-slate-300 px-4 py-8 text-sm text-slate-500 transition hover:border-brand-400 hover:bg-brand-50/40"
        >
          {file ? (
            <span className="font-medium text-slate-700">{file.name}</span>
          ) : (
            <span>Click to choose a PDF</span>
          )}
          <input
            ref={inputRef}
            id={`file-${mode}-${role}`}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
          />
        </label>

        {file && (
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {uploading ? "Uploading…" : "Upload and analyse"}
        </button>
      </div>
    </div>
  );
}
