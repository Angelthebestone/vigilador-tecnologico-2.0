// Spec 021 D4 — frontend MVP routes.
// /enterprise/login REDIRECTS to /enterprise/onboarding (no user auth, FR-038).
// /enterprise/{onboarding,chat,sources,admin} are the 4 MVP surfaces.

import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './MainLayout';
import { OnboardingFlow } from './enterprise/onboarding';
import { ToolsListPage } from './enterprise/tools';
import ChatPlaceholder from './enterprise/chat';
import SourcesPlaceholder from './enterprise/sources';
import AdminPlaceholder from './enterprise/admin';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* D4: login removed — every /enterprise/login hit redirects to onboarding. */}
        <Route
          path="/enterprise/login"
          element={<Navigate to="/enterprise/onboarding" replace />}
        />
        <Route path="/enterprise/onboarding" element={<OnboardingFlow />} />
        <Route path="/enterprise/chat" element={<ChatPlaceholder />} />
        <Route path="/enterprise/sources" element={<SourcesPlaceholder />} />
        <Route path="/enterprise/admin" element={<AdminPlaceholder />} />
        <Route path="/enterprise/tools" element={<ToolsListPage />} />
        <Route path="*" element={<MainLayout />} />
      </Routes>
    </BrowserRouter>
  );
}
