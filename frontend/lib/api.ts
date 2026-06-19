import type {
  AuthResponse,
  ChatAnswer,
  ChatMessage,
  Citation,
  DocumentSummary,
  MatchResponse,
  MultiChatAnswer,
  Note,
  ResearchExtraction,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
const TOKEN_KEY = "doclens_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

/** Thin error type so the UI can show the server's message. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      (data && (data.detail as string)) || `Request failed (${response.status})`;
    throw new ApiError(response.status, message);
  }
  return data as T;
}

export const api = {
  register: (full_name: string, email: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ full_name, email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listDocuments: () => request<DocumentSummary[]>("/documents"),

  getDocument: (id: number) => request<DocumentSummary>(`/documents/${id}`),

  uploadDocument: (
    file: File,
    title: string,
    mode: string,
    role: string = "document",
  ) => {
    const form = new FormData();
    form.append("file", file);
    form.append("title", title);
    form.append("mode", mode);
    form.append("role", role);
    return request<DocumentSummary>("/documents", { method: "POST", body: form });
  },

  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  getExtraction: (id: number) =>
    request<ResearchExtraction>(`/documents/${id}/extraction`),

  chat: (id: number, question: string) =>
    request<ChatAnswer>(`/documents/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  getMessages: (id: number) => request<ChatMessage[]>(`/documents/${id}/messages`),

  clearMessages: (id: number) =>
    request<void>(`/documents/${id}/messages`, { method: "DELETE" }),

  /**
   * Stream an answer over SSE. Calls onToken for each text chunk and resolves
   * with the final citations once the `done` event arrives.
   */
  streamChat: async (
    id: number,
    question: string,
    onToken: (text: string) => void,
  ): Promise<Citation[]> => {
    const token = getToken();
    const response = await fetch(`${API_BASE}/documents/${id}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question }),
    });
    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => null);
      throw new ApiError(response.status, (data && data.detail) || "Streaming failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let citations: Citation[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const event of events) {
        const lines = event.split("\n");
        const type = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
        const dataLine = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
        if (!dataLine) continue;
        const data = JSON.parse(dataLine);
        if (type === "token") onToken(data.text as string);
        else if (type === "done") citations = data.citations as Citation[];
      }
    }
    return citations;
  },

  match: (jobId: number, resumeIds?: number[]) =>
    request<MatchResponse>("/recruitment/match", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, resume_ids: resumeIds ?? null }),
    }),

  listNotes: (id: number) => request<Note[]>(`/documents/${id}/notes`),

  createNote: (id: number, content: string) =>
    request<Note>(`/documents/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  deleteNote: (id: number, noteId: number) =>
    request<void>(`/documents/${id}/notes/${noteId}`, { method: "DELETE" }),

  askAcrossDocuments: (question: string, documentIds?: number[]) =>
    request<MultiChatAnswer>("/documents/ask", {
      method: "POST",
      body: JSON.stringify({ question, document_ids: documentIds ?? null }),
    }),

  // Fetches the report (Markdown or PDF) as a blob; the caller downloads it.
  fetchReport: async (
    id: number,
    format: "md" | "pdf" = "md",
  ): Promise<{ filename: string; blob: Blob }> => {
    const token = getToken();
    const response = await fetch(`${API_BASE}/documents/${id}/report?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new ApiError(response.status, (data && data.detail) || "Export failed");
    }
    const disposition = response.headers.get("content-disposition") ?? "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    return { filename: match?.[1] ?? `report-${id}.${format}`, blob: await response.blob() };
  },
};
