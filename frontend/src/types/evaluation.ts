// Spec 007/008 — Evaluation workstream entity types

// WS-A: Source Quality
export type AuthorReputation = {
  authorId: string;
  name: string;
  hIndex: number;
  retractionCount: number;
  affiliation: string;
  domainWeights: Record<string, number>;
  lastRefreshed: string;
};

export type ConflictOfInterest = {
  authorId: string;
  funderEntity: string;
  corporateRatio: number;
  riskLevel: 'low' | 'medium' | 'high';
};

export type ClaimExternalValidation = {
  claimId: string;
  status: 'verified' | 'contradicted' | 'not_found';
  source: string;
  summary: string;
};

export type RetractionRecord = {
  doi: string;
  title: string;
  retractionDate: string;
  reason: string;
};

export type ReproducibilityScore = {
  sourceId: string;
  score: number;
  artifactsAvailable: boolean;
  lastChecked: string;
};

// WS-B: Data Intelligence
export type DedupedSource = {
  canonicalId: string;
  originalIds: string[];
  title: string;
  provider: string;
};

export type ContentAuthenticitySignal = {
  sourceId: string;
  aiProbability: number;
  humanProbability: number;
  verdict: 'likely_ai' | 'likely_human' | 'uncertain';
};

export type ConsensusDisputeEntry = {
  topic: string;
  agreement: boolean;
  sourceCount: number;
  confidence: number;
};

// Gráfico generado por el backend (matplotlib vía sandbox).
// `image` es una data URI o URL; `caption` la describe.
export type GeneratedChart = {
  title: string;
  image: string;
  caption: string;
};

// WS-C: Deep Analysis
export type SCurveProjection = {
  technology: string;
  domain: string;
  growthRate: number;
  inflectionYear: number;
  ceiling: number;
  rSquared: number;
  confidence: number;
  samplesCount: number;
  /** Imagen matplotlib de la curva S generada por el backend. */
  chartImage?: string;
};

export type ImplicitAssumption = {
  text: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  affectsConfidence: boolean;
};

export type CounterfactualScenario = {
  scenario: string;
  plausibility: 'low' | 'medium' | 'high';
  wouldInvalidate: string;
};

export type CriticalDependency = {
  dependencyName: string;
  impactIfRemoved: 'low' | 'medium' | 'high' | 'critical';
  alternatives: string[];
};

export type MetaAnalysisResult = {
  topic: string;
  effectSizeRange: [number, number];
  iSquared: number;
  sampleCount: number;
};

// WS-D: Strategic Signals
export type ConvergenceCluster = {
  clusterId: string;
  domains: string[];
  growthTrend: 'accelerating' | 'stable' | 'decelerating';
  density: number;
};

export type CollaborationNetwork = {
  nodes: Array<{ id: string; label: string; type: 'author' | 'institution' }>;
  edges: Array<{ source: string; target: string; weight: number; type: string }>;
};

export type IdeaLinage = {
  seminalWorkId: string;
  seminalTitle: string;
  leafWorks: Array<{ id: string; title: string; year: number }>;
};

export type NarrativeShift = {
  topic: string;
  sentimentPre: number;
  sentimentPost: number;
  direction: 'positive' | 'negative' | 'neutral';
};

export type TalentMobility = {
  personName: string;
  fromAffiliation: string;
  toAffiliation: string;
  year: number;
};

export type PatentingGap = {
  domain: string;
  classification: 'blue_ocean' | 'red_ocean';
  patentDensity: number;
  keyAssignees: string[];
};

// WS-E: Output Assurance
export type BiasAudit = {
  geographicDistribution: Record<string, number>;
  genderDistribution: Record<string, number>;
  institutionalDistribution: Record<string, number>;
  criticalBiasDetected: boolean;
  languageBias: Record<string, number>;
};

export type ForensicTrace = {
  claimId: string;
  traceSteps: Array<{
    stepType: string;
    description: string;
    confidence: number;
  }>;
};

export type StakeholderSimulation = {
  stakeholderType: string;
  critique: string;
  counterpoints: string[];
};

export type FalsificationScenario = {
  scenario: string;
  plausibility: 'low' | 'medium' | 'high';
  wouldInvalidate: string;
};

export type CalibrationCurve = {
  modelVersion: string;
  isActive: boolean;
  curvePoints: Array<{ raw: number; calibrated: number }>;
  samplesCount: number;
  /** Imagen matplotlib de la curva de calibración generada por el backend. */
  chartImage?: string;
};

// Aggregated results per workstream
export type WsaResult = {
  authorReputations: AuthorReputation[];
  conflictsOfInterest: ConflictOfInterest[];
  externalValidations: ClaimExternalValidation[];
  retractionRecords: RetractionRecord[];
  reproducibilityScores: ReproducibilityScore[];
  effectiveFreshness: number[];
};

export type WsbResult = {
  hybridSearchStats: Record<string, number>;
  dedupRate: number;
  dedupedSources: DedupedSource[];
  authenticitySignals: ContentAuthenticitySignal[];
  consensusDisputes: ConsensusDisputeEntry[];
};

export type WscResult = {
  sCurves: SCurveProjection[];
  metaAnalyses: MetaAnalysisResult[];
  implicitAssumptions: ImplicitAssumption[];
  counterfactuals: CounterfactualScenario[];
  criticalDependencies: CriticalDependency[];
  /** Gráficos matplotlib adicionales generados por el backend. */
  charts?: GeneratedChart[];
};

export type WsdResult = {
  convergenceClusters: ConvergenceCluster[];
  collaborationNetwork: CollaborationNetwork[];
  ideaLineages: IdeaLinage[];
  narrativeShifts: NarrativeShift[];
  talentMobilities: TalentMobility[];
  patentingGaps: PatentingGap[];
};

export type WseResult = {
  biasAudit: BiasAudit | null;
  forensicTraces: ForensicTrace[];
  stakeholderSimulations: StakeholderSimulation[];
  falsificationScenarios: FalsificationScenario[];
  calibrationCurve: CalibrationCurve | null;
  qualityGatePassed: boolean;
  calibratedConfidence: number | null;
};

export type SessionEvaluation = {
  sessionId: string;
  activeWorkstreams: string[];
  wsA: WsaResult | null;
  wsB: WsbResult | null;
  wsC: WscResult | null;
  wsD: WsdResult | null;
  wsE: WseResult | null;
};

// Configuration types
export type WorkstreamConfig = {
  wsA: boolean;
  wsB: boolean;
  wsC: boolean;
  wsD: boolean;
  wsE: boolean;
};

// Backend-facing kind (used in URLs and the `kind` field of payloads).
// Stays in snake_case because it's a string value, not an object key.
export type PromptKind = 'system' | 'example_user' | 'example_ai';

export type PromptVariantMeta = {
  available: boolean;
  modified: boolean;
  size: number;
};

// Frontend-facing variants record. The transform layer converts the
// snake_case keys returned by the backend (`example_user`/`example_ai`)
// into camelCase (`exampleUser`/`exampleAi`), so this is the shape we
// actually see in components.
export type PromptVariants = {
  system: PromptVariantMeta;
  exampleUser: PromptVariantMeta;
  exampleAi: PromptVariantMeta;
};

export type PromptTemplate = {
  name: string;
  modified: boolean;
  size: number;
  content?: string;
  defaultContent?: string;
  variants?: PromptVariants;
};

export type HealthStatus = {
  available: boolean;
  missingDependencies: string[];
  degradedServices: string[];
};

export type WorkstreamHealth = {
  wsA: HealthStatus;
  wsB: HealthStatus;
  wsC: HealthStatus;
  wsD: HealthStatus;
  wsE: HealthStatus;
};
