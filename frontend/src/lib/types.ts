export type Triage = "AUTO_APPROVE" | "NEEDS_MENTOR" | "BLOCKER";
export type Severity = "info" | "warning" | "critical";

export interface Scores { correctness: number; code_quality: number; security: number; testing: number; roadmap_alignment: number }
export interface InlineComment { file: string; line: number; severity: Severity; comment: string; suggestion: string }
export interface Finding { rule: string; severity: Severity; message: string; file: string; line: number | null }
export interface ReviewMeta {
  provider: string; model: string; latency_s: number; input_tokens: number; output_tokens: number;
  cost_usd: number; fallback_errors: string[]; dropped_comments: number; demo_fallback?: boolean;
}
export interface DiffLine { n: number | null; kind: "add" | "del" | "ctx"; text: string }
export interface DiffFile { path: string; language: string; lines: DiffLine[]; truncated: boolean }

export interface ReviewResponse {
  id: string; intern: string; track: string; week: string; title: string; source: string; created_at: string;
  languages: string[]; n_files: number; added: number; removed: number;
  review: { scores: Scores; overall_score: number; summary: string; inline_comments: InlineComment[]; triage: Triage };
  meta: ReviewMeta; findings: Finding[];
  similarity_top: number; similar_to: string | null; similarity_flag: boolean;
  final_triage: Triage; priority: number; reasons: string[]; minutes_saved: number; pipeline_latency_s: number;
  diff_files: DiffFile[];
}

export interface QueueItem {
  id: string; title: string; intern: string; track: string; week: string; source: string; score: number;
  triage: Triage; priority: number; critical: number; warnings: number; similarity_top: number;
  similar_to: string | null; similarity_flag: boolean; reasons: string[]; created_at: string;
}
export interface Stats {
  total: number; triage: Record<Triage, number>; auto_approved_pct: number; blockers: number; copy_flags: number;
  avg_score: number; minutes_saved: number; hours_saved: number; avg_latency_s: number;
}
export interface Health { status: string; mode: "live" | "mock"; providers: string[]; github_token: boolean; tracks: string[]; weeks: string[] }
export interface SampleMeta { id: string; title: string; intern: string; track: string; week: string; commits: string[] }

export interface ReviewRequest {
  pr_url?: string; diff?: string; sample_id?: string; track: string; week: string; intern?: string;
}
