export type SessionStatus = 'DRAFT' | 'CLARIFYING' | 'PLANNING' | 'APPROVED' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'CANCELED';

export type BranchType = 'AVANCES' | 'COMERCIAL' | 'RIESGO' | 'PI_NORMATIVA' | 'COMPETITIVO' | 'OPORTUNIDADES';

export type ChatMessageType = 'user' | 'system' | 'event' | 'plan' | 'report' | 'clarification';

export type ChatMessage = {
  id: string;
  type: ChatMessageType;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

export type ThinkingStep = {
  stepNumber: number;
  reasoning: string;
  toolCall?: {
    tool: string;
    query: string;
    result: string;
  };
  result?: string;
  confidence: number;
};

export type BranchAgentStatus = 'waiting' | 'running' | 'completed' | 'failed';

export type BranchAgent = {
  branchType: BranchType;
  status: BranchAgentStatus;
  currentIteration: number;
  totalIterations: number;
  iterations: ThinkingStep[];
  confidence: number;
  error?: string;
};

export type GraphNode = {
  id: string;
  label: string;
  centrality: number;
  branchType: BranchType;
  sourceIds: string[];
  confidence: number;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  relationType: string;
  similarityScore: number;
};

export type GraphData = {
  sessionId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type Source = {
  id: string;
  url: string;
  title: string | null;
  provider: string;
  branchType: BranchType;
  accessedAt: string;
};

export type Recommendation = {
  text: string;
  priority: 'alta' | 'media' | 'baja';
  basedOn: string[];
};

export type ProviderMetric = {
  providerName: string;
  avgLatencyMs: number;
  errorRate: number;
  retryRate: number;
  latencyBuckets: Record<string, number>;
};

export type SessionSummary = {
  id: string;
  query: string;
  date: string;
  status: SessionStatus;
};

export type FinalReport = {
  sessionId: string;
  markdown: string;
  executiveSummary: string;
  technicalSection: string;
  commercialSection: string;
  riskSection: string;
  crossAnalysis: string;
  recommendations: Recommendation[];
  totalSourcesConsulted: number;
  totalLearnings: number;
  confidenceScore: number;
  generatedAt: string;
};

export type ResearchPlan = {
  id: string;
  version: number;
  branches: BranchConfig[];
  requiresApproval: boolean;
  globalConstraints: Record<string, unknown>;
};

export type BranchConfig = {
  branchType: BranchType;
  focusQueries: string[];
  mcpProviders: string[];
  priorityWeight?: number;
};

export type SSEConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export type SessionState = {
  id: string;
  query: string;
  status: SessionStatus;
  plan: ResearchPlan | null;
  report: FinalReport | null;
};

export type BranchKPI = {
  branchType: BranchType;
  coverageKpi: number;
  precisionKpi: number;
  latencyMsKpi: number;
  costKpi: number;
};

export type AnalysisMetrics = {
  branchKpis: BranchKPI[];
  providerMetrics: ProviderMetric[];
  confidenceScore: number;
  totalSources: number;
  totalFindings: number;
};
