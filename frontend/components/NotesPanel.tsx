"use client";

import { useCallback, useEffect, useState } from "react";

import { StickyNote } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { Note } from "@/lib/types";

export default function NotesPanel({ documentId }: { documentId: number }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setNotes(await api.listNotes(documentId));
  }, [documentId]);

  useEffect(() => {
    load();
  }, [load]);

  async function add(event: React.FormEvent) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || saving) return;
    setSaving(true);
    setError(null);
    try {
      await api.createNote(documentId, content);
      setDraft("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the note.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(noteId: number) {
    await api.deleteNote(documentId, noteId);
    load();
  }

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 className="flex items-center gap-2 font-semibold text-slate-900">
        <StickyNote className="h-4 w-4 text-brand-600" />
        Notes
      </h2>

      <form onSubmit={add} className="mt-3 space-y-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          placeholder="Jot down a thought about this document…"
          className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={saving || !draft.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {saving ? "Saving…" : "Add note"}
        </button>
      </form>

      {notes.length > 0 && (
        <ul className="mt-4 space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="group flex items-start justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700 ring-1 ring-slate-200"
            >
              <span className="whitespace-pre-wrap">{note.content}</span>
              <button
                onClick={() => remove(note.id)}
                className="shrink-0 text-xs text-slate-400 opacity-0 transition group-hover:opacity-100 hover:text-red-600"
                aria-label="Delete note"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
