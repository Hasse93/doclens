"use client";

import Link from "next/link";
import { ArrowRight, Code2, Layers, ListChecks, Quote } from "lucide-react";

import { useAuth } from "@/lib/auth";

const FEATURES = [
  {
    icon: Quote,
    title: "Cited answers",
    body: "Ask questions and get answers grounded in the source — every claim links back to the exact page.",
  },
  {
    icon: ListChecks,
    title: "Structured extraction",
    body: "Pull clean, schema-validated fields from any document — methodology, datasets, skills, and more.",
  },
  {
    icon: Layers,
    title: "Two modes, one engine",
    body: "Understand academic papers, or rank résumés against a job description — from the same RAG core.",
  },
];

export default function Home() {
  const { user, loading } = useAuth();
  const primaryHref = user ? "/dashboard" : "/register";
  const primaryLabel = user ? "Open dashboard" : "Get started";

  return (
    <main className="min-h-screen bg-gradient-to-b from-brand-50 via-white to-white dark:from-slate-900 dark:via-slate-950 dark:to-slate-950">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <span className="flex items-center gap-2 font-semibold text-slate-900 dark:text-slate-100">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm text-white">
            DL
          </span>
          DocLens
        </span>
        <nav className="flex items-center gap-2 text-sm">
          {!loading && !user && (
            <Link
              href="/login"
              className="rounded-lg px-3 py-1.5 font-medium text-slate-600 transition hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
            >
              Sign in
            </Link>
          )}
          <Link
            href={primaryHref}
            className="rounded-lg bg-brand-600 px-4 py-1.5 font-medium text-white transition hover:bg-brand-700"
          >
            {primaryLabel}
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-3xl px-6 pb-16 pt-16 text-center sm:pt-24">
        <span className="inline-block rounded-full bg-brand-100 px-3 py-1 text-xs font-medium text-brand-700 dark:bg-brand-500/15 dark:text-brand-100">
          AI document intelligence
        </span>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-50 sm:text-5xl">
          See into your documents
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-slate-600 dark:text-slate-300">
          Upload a PDF and DocLens reads it for you — summaries, answers grounded in
          citations, and structured insights. Built for research papers and recruiting alike.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href={primaryHref}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-3 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700"
          >
            {primaryLabel}
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="https://github.com/Hasse93/doclens"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-6 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            <Code2 className="h-4 w-4" />
            View source
          </a>
        </div>
      </section>

      <section className="mx-auto grid max-w-5xl gap-5 px-6 pb-24 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:shadow-md dark:bg-slate-900 dark:ring-slate-800"
          >
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-500/15 dark:text-brand-100">
              <f.icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-semibold text-slate-900 dark:text-slate-100">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{f.body}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
