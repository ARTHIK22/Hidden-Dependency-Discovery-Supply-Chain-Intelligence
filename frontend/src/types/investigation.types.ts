export type InvestigationStatus = "draft" | "running" | "paused" | "completed" | "failed" | "archived";
export interface Investigation { id: string; organization_id: string | null; created_by: string | null; name: string; target: string | null; description: string | null; status: InvestigationStatus; priority: string; created_at: string; updated_at: string }
export interface InvestigationCreate { name: string; target?: string | null; description?: string | null; priority?: "low" | "medium" | "high" | "critical" }
export type InvestigationUpdate = Partial<InvestigationCreate> & { status?: InvestigationStatus };
export interface InvestigationStep { id: string; sequence: number; stage: string; status: "pending" | "running" | "completed" | "skipped" | "failed"; input_data: Record<string, unknown>; output_data: Record<string, unknown>; error_message: string | null; started_at: string | null; completed_at: string | null; created_at: string }
