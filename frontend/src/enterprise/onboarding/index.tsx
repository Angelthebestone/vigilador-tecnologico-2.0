// Spec 021 D4 / T115 — onboarding surface index.
// Re-exports the existing wizard as the canonical entry; the wizard itself
// is being extended to call the four spec-021 endpoints (POST /company,
// /providers, /connectors/drive, /ingest/initial). The legacy 2-step wizard
// stays in place until the F4a.G UI work lands.
export { OnboardingFlow as default } from './OnboardingFlow';
export { OnboardingFlow } from './OnboardingFlow';
