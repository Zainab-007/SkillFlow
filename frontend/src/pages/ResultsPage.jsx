import React from 'react';

/**
 * ResultsPage component (Phase 1 Placeholder).
 * Displays the accumulated profile in a human-readable summary
 * and a placeholder indicating recommendation pathways will follow.
 *
 * @param {Object} props
 * @param {Object} props.profile - Accumulated livelihood profile from session
 * @param {string} props.language - 'en' or 'hi'
 * @param {function(): void} props.onRestart - Restart interview callback
 */
export default function ResultsPage({ profile = {}, language = 'en', onRestart }) {
  const isHindi = language === 'hi';

  const formatList = (val) => {
    if (Array.isArray(val) && val.length > 0) {
      return val;
    }
    return null;
  };

  const skillsList = formatList(profile.skills);
  const interestsList = formatList(profile.interests);

  return (
    <div className="results-card" aria-labelledby="results-title">
      <header className="results-header">
        <div className="results-badge">
          <span>✓</span>
          <span>{isHindi ? 'प्रोफ़ाइल तैयार है' : 'Assessment Complete'}</span>
        </div>
        <h1 id="results-title" className="results-title">
          {isHindi ? 'आपकी स्किलफ्लो प्रोफ़ाइल' : 'Your SkillFlow profile is ready.'}
        </h1>
        <p className="results-subtitle">
          {isHindi
            ? 'आपकी बातचीत के आधार पर तैयार की गई आजीविका प्रोफ़ाइल'
            : 'Livelihood profile synthesized from your conversation'}
        </p>
      </header>

      {/* Human-readable profile summary grid */}
      <section className="profile-summary-grid">
        <div className="summary-card">
          <div className="summary-card-label">
            {isHindi ? 'वर्तमान कार्य' : 'Current Work'}
          </div>
          <div className="summary-card-value">
            {profile.current_occupation || (isHindi ? 'उल्लेख नहीं' : 'Not specified')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">
            {isHindi ? 'कार्य अनुभव' : 'Experience'}
          </div>
          <div className="summary-card-value">
            {profile.experience_years !== undefined && profile.experience_years !== null
              ? `${profile.experience_years} ${isHindi ? 'वर्ष' : 'years'}`
              : isHindi
                ? 'उल्लेख नहीं'
                : 'Not specified'}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">
            {isHindi ? 'शिक्षा' : 'Education'}
          </div>
          <div className="summary-card-value">
            {profile.education || (isHindi ? 'उल्लेख नहीं' : 'Not specified')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">
            {isHindi ? 'स्थान' : 'Location'}
          </div>
          <div className="summary-card-value">
            {profile.location || (isHindi ? 'उल्लेख नहीं' : 'Not specified')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">
            {isHindi ? 'रोजगार प्राथमिकता' : 'Work Preference'}
          </div>
          <div className="summary-card-value">
            {profile.employment_preference || (isHindi ? 'उल्लेख नहीं' : 'Not specified')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">
            {isHindi ? 'कार्य परिवेश / गतिशीलता' : 'Work Setting'}
          </div>
          <div className="summary-card-value">
            {profile.mobility_constraint || (isHindi ? 'सामान्य' : 'Flexible')}
          </div>
        </div>

        {/* Skills */}
        <div className="summary-card" style={{ gridColumn: '1 / -1' }}>
          <div className="summary-card-label">
            {isHindi ? 'दर्ज कौशल एवं हुनर' : 'Skills'}
          </div>
          {skillsList ? (
            <div className="summary-card-pills">
              {skillsList.map((skill, idx) => (
                <span key={`${skill}-${idx}`} className="skill-pill">
                  {skill}
                </span>
              ))}
            </div>
          ) : (
            <div className="summary-card-value">
              {isHindi ? 'कोई कौशल दर्ज नहीं' : 'No specific skills recorded'}
            </div>
          )}
        </div>

        {/* Interests */}
        {interestsList && (
          <div className="summary-card" style={{ gridColumn: '1 / -1' }}>
            <div className="summary-card-label">
              {isHindi ? 'रुचियां एवं पसंदीदा क्षेत्र' : 'Interests'}
            </div>
            <div className="summary-card-pills">
              {interestsList.map((interest, idx) => (
                <span
                  key={`${interest}-${idx}`}
                  className="skill-pill"
                  style={{ background: 'var(--emerald-50)', color: 'var(--emerald-600)' }}
                >
                  {interest}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Next steps notice — matching connected in subsequent phase */}
      <section className="next-steps-banner">
        <h4>{isHindi ? 'प्रशिक्षण एवं आजीविका सिफ़ारिशें' : 'Recommendations coming next.'}</h4>
        <p>
          {isHindi
            ? 'पीएम-अजय (PM-AJAY) के तहत 20 राष्ट्रीय कौशल योग्यता फ्रेमवर्क (NSQF) भूमिकाओं के साथ मिलान अगले चरण में उपलब्ध कराया जाएगा।'
            : 'NSQF-aligned livelihood and skill pathway matching will be presented here in the next milestone.'}
        </p>
      </section>

      <div className="results-actions">
        <button
          type="button"
          className="btn-secondary"
          onClick={onRestart}
          id="restart-interview-btn"
        >
          <span>↺</span>
          <span>{isHindi ? 'नया साक्षात्कार शुरू करें' : 'Start New Interview'}</span>
        </button>
      </div>
    </div>
  );
}
