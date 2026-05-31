import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import './styles/globals.css';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import SettingsPage from './pages/SettingsPage';
import ErrorBoundary from './components/ErrorBoundary';
import { AuthProvider } from './contexts/AuthContext';

function App() {
  if (typeof window !== 'undefined') {
    const pathname = window.location.pathname || '/';
    const hash = window.location.hash || '';
    const isStaticAsset = /\.[a-zA-Z0-9]+$/.test(pathname);

    if (pathname !== '/' && !isStaticAsset) {
      const normalizedHash = hash.startsWith('#/') ? hash.slice(1) : pathname;
      const target = `/#${normalizedHash.startsWith('/') ? normalizedHash : `/${normalizedHash}`}`;
      if (`${pathname}${hash}` !== target) {
        window.location.replace(target);
        return null;
      }
    }
  }

  return (
    <>
      <div className="animated-bg" />
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/settings" element={<ErrorBoundary><SettingsPage /></ErrorBoundary>} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </>
  );
}

export default App;
