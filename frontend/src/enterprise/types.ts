export interface CompanyProfile {
  name: string;
  sector?: string;
  country?: string;
  department?: string;
  municipality?: string;
  timezone?: string;
}

export interface LlmProviderState {
  provider: string;
  model?: string;
}

export interface ToolCard {
  id: string;
  description: string;
  domains: string[];
  requiresAuth: boolean;
  costTier: string;
  status: string;
}
