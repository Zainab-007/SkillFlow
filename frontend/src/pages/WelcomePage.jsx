import React from 'react';
import LanguageSelector from '../components/LanguageSelector';

/**
 * WelcomePage component.
 * Landing screen introducing SkillFlow with language selection and start button.
 *
 * @param {Object} props
 * @param {string} props.selectedLanguage - 'en' or 'hi'
 * @param {function(string): void} props.onSelectLanguage
 * @param {function(): void} props.onStartConversation
 */
export default function WelcomePage({
  selectedLanguage,
  onSelectLanguage,
  onStartConversation,
}) {
  const isHindi = selectedLanguage === 'hi';

  return (
    <section className="welcome-hero" aria-labelledby="welcome-heading">
      <div className="welcome-badge">
        <span>🇮🇳</span>
        <span>
          {isHindi
            ? 'पीएम-अजय (PM-AJAY) आजीविका एवं कौशल सहायक'
            : 'PM-AJAY Livelihood & Skilling Assistant'}
        </span>
      </div>

      <h1 id="welcome-heading" className="welcome-title">
        SkillFlow
      </h1>

      <p className="welcome-tagline">
        {isHindi
          ? '« जो आप जानते हैं, उससे जहाँ आप पहुँच सकते हैं »'
          : '“From what you know to where you can go.”'}
      </p>

      <p className="welcome-description">
        {isHindi
          ? 'हमें अपने कौशल, अनुभव और रुचियों के बारे में बताएं। स्किलफ्लो आपकी प्रोफ़ाइल को समझेगा और उपयुक्त आजीविका तथा कौशल प्रशिक्षण के मार्ग सुझाएगा।'
          : 'Tell us about your skills, experience and interests. SkillFlow will understand your profile and suggest suitable livelihood and training pathways.'}
      </p>

      <div className="language-section">
        <label className="language-label">
          {isHindi ? 'बातचीत की भाषा चुनें / Select Language:' : 'Select your conversation language:'}
        </label>
        <LanguageSelector
          selectedLanguage={selectedLanguage}
          onSelect={onSelectLanguage}
        />
      </div>

      <div>
        <button
          type="button"
          id="start-conversation-btn"
          className="btn-start"
          onClick={onStartConversation}
        >
          <span>{isHindi ? 'बातचीत शुरू करें' : 'Start Conversation'}</span>
          <span>➔</span>
        </button>
      </div>
    </section>
  );
}
