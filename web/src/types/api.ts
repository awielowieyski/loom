// ---- Enums ----

export type TrustTier = 'experimental' | 'community' | 'verified'
export type CostProfile = 'free' | 'low' | 'moderate' | 'high'
export type EstimatedDuration = 'fast' | 'moderate' | 'slow'
export type Scope = 'community' | 'corporate'
export type UsageOutcome = 'success' | 'partial' | 'failure'
export type WindowType = '7d' | '30d' | '90d'
export type EvalStatus = 'pending' | 'running' | 'completed' | 'failed'
export type TriggerType = 'submission' | 'amendment' | 'scheduled' | 'usage_signal'
export type EvalDimension = 'clarity' | 'completeness' | 'safety' | 'correctness'
export type BehavioralEvalApplicability = 'auto' | 'not_applicable' | 'required'
export type AmendmentClassification =
  | 'refinement'
  | 'regression'
  | 'variant'
  | 'extension'
  | 'rejected'
export type InputLogging = 'none' | 'anonymised' | 'full' | 'unknown'
export type DataRetention = 'none' | 'transient' | 'persistent' | 'unknown'
export type DataClassification = 'none' | 'internal' | 'confidential'

// ---- Common models ----

export interface PrivacyImpact {
  external_data_sharing: boolean
  input_logging: InputLogging
  data_retention: DataRetention
}

export interface TrustRequirements {
  data_classification: DataClassification
  network_access: boolean
  privacy_impact: PrivacyImpact
}

export interface MCPServerDependency {
  uri: string
  required: boolean
  scopes: string[]
}

export interface APIDependency {
  name: string
  auth_type: string
  scopes: string[]
}

export interface DependencyDeclaration {
  mcp_servers: MCPServerDependency[]
  apis: APIDependency[]
  trust_requirements: TrustRequirements
}

export interface EvalScenario {
  description: string
  input_context: string
  success_criteria: string
}

export interface QualityDimension {
  name: string
  description: string
}

export interface EvalSpec {
  scenarios: EvalScenario[]
  quality_dimensions: QualityDimension[]
  behavioral_eval: BehavioralEvalApplicability
}

// ---- Skill ----

export interface Skill {
  id: string
  slug: string
  name: string
  description: string
  content: string
  category_id: string
  tags: string[]
  scope: string
  version: string
  author_id: string
  trust_tier: TrustTier
  cost_profile: CostProfile
  cost_drivers: string[]
  estimated_duration: string
  dependencies: DependencyDeclaration
  eval_spec: EvalSpec
  signature: string | null
  extends: string | null
  eval_status: string | null
  composite_score: number | null
  latest_eval_job_id: string | null
  signature_key_fingerprint: string | null
  deprecated_at: string | null
  successor_slug: string | null
  stale_since: string | null
  behavioral_score: number | null
  last_eval_at: string | null
  resolution_count: number
  created_at: string | null
  updated_at: string | null
}

export interface SkillSummary {
  id: string
  slug: string
  name: string
  description: string
  category_id: string
  tags: string[]
  version: string
  trust_tier: TrustTier
  cost_profile: CostProfile
  estimated_duration: string
}

// ---- Capability ----

export interface CapabilityStep {
  skill_ref: string
  role: string
  inputs: Record<string, string>
  outputs: Record<string, string>
  required: boolean
  data_classification: string
}

export interface DataFlowEdge {
  from_step: string
  to_step: string
  classification: string
}

export interface Capability {
  id: string
  slug: string
  name: string
  description: string
  category_id: string
  tags: string[]
  scope: string
  version: string
  author_id: string
  trust_tier: TrustTier
  steps: CapabilityStep[]
  preconditions: string[]
  expected_outcome: string
  data_flow: DataFlowEdge[]
  dependencies: DependencyDeclaration
  cost_profile: CostProfile
  cost_drivers: string[]
  estimated_duration: string
  eval_spec: EvalSpec
  extends: string | null
  eval_status: string | null
  composite_score: number | null
  created_at: string | null
  updated_at: string | null
}

export interface CapabilitySummary {
  id: string
  slug: string
  name: string
  description: string
  category_id: string
  tags: string[]
  version: string
  trust_tier: TrustTier
  cost_profile: CostProfile
  estimated_duration: string
  step_count: number
}

// ---- Resolution ----

export interface ResolutionContext {
  trust_floor?: TrustTier | null
  cost_budget?: CostProfile | null
  latency_budget?: string | null
  data_classification?: string | null
  available_tools?: string[]
  approved_providers?: string[]
  runtime?: string | null
}

export interface Alternative {
  skill: SkillSummary
  match_score: number
  tradeoff: string
}

export interface RejectedCandidate {
  skill: SkillSummary
  reason: string
}

export interface ResolvedSkill {
  skill: Skill
  dependencies_satisfied: string[]
  dependencies_missing: string[]
  alternatives: Alternative[]
  rejected_candidates: RejectedCandidate[]
  selection_rationale: string[]
}

export interface ResolvedStep {
  index: number
  skill_ref: string
  role: string
  skill: Skill
  inputs: Record<string, string>
  outputs: Record<string, string>
  required: boolean
  data_classification: string
  dependencies_satisfied: string[]
  dependencies_missing: string[]
}

export interface ResolvedCapability {
  capability: Capability
  resolved_steps: ResolvedStep[]
  effective_trust_tier: TrustTier
  trust_warnings: string[]
  all_dependencies_satisfied: string[]
  all_dependencies_missing: string[]
  data_flow: DataFlowEdge[]
  alternatives: Alternative[]
  selection_rationale: string[]
}

export interface ResolvedResult {
  type: 'skill' | 'capability'
  skill: ResolvedSkill | null
  capability: ResolvedCapability | null
}

export interface ResolutionError {
  error: string
  message: string
  suggestions: string[] | null
  available_at_lower_tier: SkillSummary[] | null
  successor: string | null
}

// ---- Eval ----

export interface DimensionResult {
  dimension: EvalDimension
  score: number
  evidence: string[]
  injection_detected: boolean
  injection_detail: string | null
  confidence: number
  prompt_variant: string
  model_id: string
}

export interface EvalResult {
  passed: boolean
  composite_score: number
  dimension_scores: Record<string, number>
  dimension_confidence: Record<string, number>
  overall_confidence: number
  injection_flagged: boolean
  sandbox_passed: boolean | null
  content_hash: string
  evaluator_version: string
}

// ---- Usage ----

export interface UsageReport {
  id: string
  idempotency_key: string
  skill_id: string
  skill_version: string
  outcome: UsageOutcome
  runtime_ms: number | null
  context_hash: string | null
  failure_reason: string | null
  created_at: string | null
}

export interface UsageAggregate {
  id: string
  skill_id: string
  skill_version: string
  window_type: WindowType
  success_count: number
  partial_count: number
  failure_count: number
  success_rate: number | null
  avg_runtime_ms: number | null
  skip_count: number
  computed_at: string | null
  window_start: string | null
}

export interface UsageStats {
  slug: string
  aggregates: UsageAggregate[]
}

// ---- Behavioral ----

export interface RunnerOutput {
  actions_taken: string[]
  output: string
  artifacts: string[]
  notes: string | null
}

export interface JudgeScore {
  outcome_quality: number
  completeness: number
  efficiency: number
  evidence: string
  confidence: number
  injection_detected: boolean
}

export interface BehavioralRunResult {
  id: string
  eval_job_id: string
  scenario_index: number
  run_index: number
  runner_output: RunnerOutput
  judge_score: number
  judge_evidence: JudgeScore
  judge_confidence: number
  injection_detected: boolean
  runner_model_id: string
  judge_model_id: string
  runner_latency_ms: number | null
  judge_latency_ms: number | null
  created_at: string | null
}

export interface BehavioralEvalResult {
  behavioral_score: number
  run_count: number
  scenario_count: number
  variance: number
  per_run: BehavioralRunResult[]
}

// ---- Category ----

export interface Category {
  id: string
  slug: string
  name: string
  description: string | null
  parent_id: string | null
  created_at: string | null
}

// ---- Activity Feed ----

export interface ActivityEvent {
  id: string
  type: 'skill_created' | 'skill_updated' | 'eval_completed' | 'resolution' | 'usage_report'
  timestamp: string
  title: string
  description: string
  slug?: string
  metadata?: Record<string, unknown>
}

export interface ActivityFeedResponse {
  events: ActivityEvent[]
  has_more: boolean
  cursor?: string
}

// ---- Stats / Dashboard ----

export interface StatsOverview {
  skill_counts: Record<TrustTier, number>
  capability_count: number
  behavioral_eval_coverage: number
  stale_count: number
  deprecated_count: number
  total_resolutions_7d: number
  total_resolutions_30d: number
}

export interface EvalTrendWindow {
  week: string
  p25: number | null
  p50: number | null
  p75: number | null
  behavioral_p50: number | null
  eval_count: number
}

export interface EvalTrendsResponse {
  weeks_requested: number
  category: string | null
  windows: EvalTrendWindow[]
}

export interface UsageHeatmapResponse {
  period_type: string
  categories: string[]
  periods: string[]
  data: number[][]
}

export type GovernanceReason = 'injection_flag' | 'low_confidence' | 'recent_amendment'

export interface GovernanceQueueItem {
  id: string
  skill_id: string
  slug: string
  name: string
  reason: GovernanceReason
  submitted_at: string | null
  eval_summary: {
    composite_score?: number | null
    dimension_scores?: Record<string, number> | null
    injection_flagged?: boolean
    changelog?: string | null
  }
}

export interface GovernanceReviewSubmission {
  queue_item_id: string
  decision: 'approve' | 'reject' | 'request_changes'
  note: string
}

export interface EmbeddingMapPoint {
  slug: string
  name: string
  type: 'skill' | 'capability'
  x: number
  y: number
  trust_tier: TrustTier
  composite_score: number | null
  category: string
}

export interface EmbeddingMapSkill {
  slug: string
  name: string
  x: number
  y: number
  trust_tier: TrustTier
  category: string
  composite_score: number | null
  behavioral_score: number | null
}

export interface EmbeddingMapCapability {
  slug: string
  name: string
  x: number
  y: number
  trust_tier: TrustTier
  category: string
  composite_score: number | null
  step_slugs: string[]
}

export interface EmbeddingMapData {
  skills: EmbeddingMapSkill[]
  capabilities: EmbeddingMapCapability[]
}

// ---- Timeline ----

export interface TimelineEntry {
  version: string
  created_at: string
  changelog: string | null
  composite_score: number | null
  eval_status: string | null
}

export interface SkillTimelineEvent {
  timestamp: string
  event_type: 'submitted' | 'eval_completed' | 'promoted' | 'demoted' | 'version'
  detail: string
}

export interface SkillTimelineResponse {
  events: SkillTimelineEvent[]
}
