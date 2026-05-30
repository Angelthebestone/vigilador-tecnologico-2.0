import { useEffect } from 'react';
import { useOnboardingStore } from '../state/onboardingStore';
import { Step1Company } from './Step1Company';
import { Step2LlmProvider } from './Step2LlmProvider';

export function OnboardingFlow() {
  const { currentStep, loadFromBackend } = useOnboardingStore();

  useEffect(() => { loadFromBackend(); }, [loadFromBackend]);

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', padding: 24 }}>
      {currentStep === 1 ? <Step1Company /> : <Step2LlmProvider />}
    </div>
  );
}
