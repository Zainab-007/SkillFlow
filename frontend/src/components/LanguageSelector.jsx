import React from 'react';

/**
 * LanguageSelector component.
 * Allows choosing between English and Hindi.
 *
 * @param {Object} props
 * @param {string} props.selectedLanguage - 'en' or 'hi'
 * @param {function(string): void} props.onSelect - Callback when language is picked
 * @param {boolean} [props.disabled=false]
 */
export default function LanguageSelector({ selectedLanguage, onSelect, disabled = false }) {
  return (
    <div className="language-options" role="radiogroup" aria-label="Select conversation language">
      <button
        type="button"
        role="radio"
        aria-checked={selectedLanguage === 'en'}
        className={`lang-btn ${selectedLanguage === 'en' ? 'active' : ''}`}
        onClick={() => onSelect('en')}
        disabled={disabled}
      >
        <span>English</span>
        <span className="subtext">English conversation</span>
      </button>

      <button
        type="button"
        role="radio"
        aria-checked={selectedLanguage === 'hi'}
        className={`lang-btn ${selectedLanguage === 'hi' ? 'active' : ''}`}
        onClick={() => onSelect('hi')}
        disabled={disabled}
      >
        <span style={{ fontFamily: 'var(--font-hindi)' }}>हिंदी</span>
        <span className="subtext">बातचीत हिंदी में</span>
      </button>
    </div>
  );
}
