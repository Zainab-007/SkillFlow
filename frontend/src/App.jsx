import React, { useState, useEffect } from 'react';
import WelcomePage from './pages/WelcomePage';
import InterviewPage from './pages/InterviewPage';
import ResultsPage from './pages/ResultsPage';

/**
 * SkillFlow Main Application Component.
 * Orchestrates navigation across Welcome, Interview, and Results screens.
 */
export default function App() {
  const [currentPage, setCurrentPage] = useState('welcome'); // 'welcome' | 'interview' | 'results'
  const [language, setLanguage] = useState('en'); // 'en' | 'hi'
  const [sessionId, setSessionId] = useState('');
  const [finalProfile, setFinalProfile] = useState({});

  // Sync html lang attribute
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const handleStartConversation = () => {
    const newSessionId = `skillflow-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setSessionId(newSessionId);
    setCurrentPage('interview');
  };

  const handleInterviewComplete = (collectedProfile) => {
    setFinalProfile(collectedProfile);
    setCurrentPage('results');
  };

  const handleResetToWelcome = () => {
    setCurrentPage('welcome');
    setSessionId('');
    setFinalProfile({});
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="top-navbar">
        <div
          className="brand-wrap"
          onClick={handleResetToWelcome}
          style={{ cursor: 'pointer' }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && handleResetToWelcome()}
        >
          <div className="brand-logo-badge">SF</div>
          <span className="brand-title">SkillFlow</span>
          <span className="brand-subtitle">SIH26097 · PM-AJAY</span>
        </div>

        <div className="nav-actions">
          {currentPage !== 'welcome' && (
            <span
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--slate-600)',
                background: 'var(--slate-100)',
                padding: '0.25rem 0.6rem',
                borderRadius: 'var(--radius-full)',
              }}
            >
              🌐 {language === 'hi' ? 'हिंदी' : 'English'}
            </span>
          )}

          {currentPage !== 'welcome' && (
            <button
              type="button"
              className="btn-secondary"
              style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
              onClick={handleResetToWelcome}
            >
              {language === 'hi' ? 'मुख्य पृष्ठ' : 'Start Over'}
            </button>
          )}
        </div>
      </header>

      {/* Main Page Content */}
      <main className="main-content">
        {currentPage === 'welcome' && (
          <WelcomePage
            selectedLanguage={language}
            onSelectLanguage={setLanguage}
            onStartConversation={handleStartConversation}
          />
        )}

        {currentPage === 'interview' && (
          <InterviewPage
            sessionId={sessionId}
            language={language}
            onInterviewComplete={handleInterviewComplete}
            onReset={handleResetToWelcome}
          />
        )}

        {currentPage === 'results' && (
          <ResultsPage
            profile={finalProfile}
            language={language}
            onRestart={handleResetToWelcome}
          />
        )}
      </main>
    </div>
  );
}
