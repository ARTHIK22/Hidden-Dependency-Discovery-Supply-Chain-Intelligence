export interface RiskSignal { category: string; severity: string; score: number; entity_id: string; entity_name?: string; affected_entities: string[]; explanation: string }
export interface RiskAnalysis { risks: RiskSignal[]; basis: string; external_risk_feeds_used: boolean }
