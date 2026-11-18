export type RiskLevel = 'low' | 'medium' | 'high' | 'unknown'
export type ScoredCategory = {
  category: string
  points: number
  action: { type: string; status: string; evidence: string; stage?: number }
}
export type ScoreBreakdown = {
  base_score: number | null
  safe_categories: ScoredCategory[]
  safe_points: number
  protected_base: number | null
  risk_categories: ScoredCategory[]
  risk_penalty: number
  adjustments: { reason: string; before: number; after: number }[]
  unscored_reason: string | null
  final_score: number | null
}
export type DiagnosisReport = {
  score?: number | null
  scoring_version?: string
  score_breakdown?: ScoreBreakdown | null
  risk_level: RiskLevel
  risk_label: string
  summary: string
  completed_stage_count: number
  total_stages: number
  safe_actions: string[]
  risky_actions: string[]
  recommended_actions: string[]
  conversation_history?: { stage: number; speaker: string; message: string; kind?: 'situation' }[]
}
