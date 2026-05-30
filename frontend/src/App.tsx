import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './MainLayout';
import { LoginPage } from './enterprise/auth';
import { OnboardingFlow } from './enterprise/onboarding';
import { ToolsListPage } from './enterprise/tools';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/enterprise/login" element={<LoginPage />} />
        <Route path="/enterprise/onboarding" element={<OnboardingFlow />} />
        <Route path="/enterprise/tools" element={<ToolsListPage />} />
        <Route path="*" element={<MainLayout />} />
      </Routes>
    </BrowserRouter>
  );
}
