export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentSummary {
  id: number;
  title: string;
  filename: string;
  mode: string;
  role: string;
  status: DocumentStatus;
  error: string | null;
  page_count: number;
  summary: string | null;
  created_at: string;
}

export interface Citation {
  marker: number;
  page_number: number;
  snippet: string;
}

export interface ChatAnswer {
  answer: string;
  citations: Citation[];
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface ResearchExtraction {
  title: string | null;
  authors: string[];
  methodology: string | null;
  dataset: string | null;
  key_findings: string[];
  limitations: string | null;
}

export interface RecruitmentExtraction {
  name: string | null;
  email: string | null;
  current_title: string | null;
  skills: string[];
  years_experience: number | null;
  education: string[];
}

export interface MatchResult {
  resume_id: number;
  resume_title: string;
  score: number;
  semantic_score: number;
  matched_skills: string[];
  missing_skills: string[];
  recommendation: string;
}

export interface MatchResponse {
  job_id: number;
  job_title: string;
  results: MatchResult[];
}

export interface Note {
  id: number;
  document_id: number;
  content: string;
  created_at: string;
}

export interface MultiCitation {
  marker: number;
  document_id: number;
  document_title: string;
  page_number: number;
  snippet: string;
}

export interface MultiChatAnswer {
  answer: string;
  citations: MultiCitation[];
}
