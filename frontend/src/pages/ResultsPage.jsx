import React from 'react';

/**
 * ResultsPage component.
 * Displays top 3 explainable NSQF recommendations, grounded explanations,
 * skill-gap analysis, and verified training roadmaps.
 *
 * @param {Object} props
 * @param {Object} props.profile - Accumulated livelihood profile from session
 * @param {Array<Object>} props.recommendations - Top recommended roles from /api/recommendations
 * @param {boolean} props.isLoading - Whether recommendations are loading
 * @param {string|null} props.error - Error message if fetch failed
 * @param {string} props.language - 'en' or 'hi'
 * @param {function(): void} props.onRestart - Restart interview callback
 * @param {function(): void} [props.onRetry] - Retry recommendations callback
 */
export default function ResultsPage({
  profile = {},
  recommendations = [],
  isLoading = false,
  error = null,
  language = 'en',
  onRestart,
  onRetry,
}) {
  const isHindi = language === 'hi';

  // 1. Loading State ("Finding pathways for you...")
  if (isLoading) {
    return (
      <div className="results-card" role="status" aria-live="polite">
        <div className="pathways-loading-state">
          <div className="loading-radar-ring" />
          <h2 className="loading-headline">
            {isHindi ? 'आपके लिए आजीविका मार्ग खोज रहे हैं...' : 'Finding pathways for you...'}
          </h2>
          <p className="loading-subtext">
            {isHindi
              ? 'आपकी बातचीत, कौशल और प्राथमिकताओं का 20 राष्ट्रीय व्यावसायिक योग्यताओं (NSQF) के साथ विश्लेषण किया जा रहा है।'
              : 'Analysing your profile, skills, and preferences against accredited NSQF vocational pathways.'}
          </p>
        </div>
      </div>
    );
  }

  const formatList = (val) => (Array.isArray(val) && val.length > 0 ? val : null);
  const userSkills = formatList(profile.skills);
  const userInterests = formatList(profile.interests);

  return (
    <div className="results-card" aria-labelledby="results-title">
      {/* Top Banner Header */}
      <header className="results-header">
        <div className="results-badge">
          <span>✓</span>
          <span>{isHindi ? 'सिफ़ारिशें तैयार हैं' : 'Pathways Ready'}</span>
        </div>
        <h1 id="results-title" className="results-title">
          {isHindi ? 'आपके स्किलफ्लो आजीविका मार्ग' : 'Your SkillFlow Pathways'}
        </h1>
        <p className="results-subtitle">
          {isHindi
            ? 'आपके कौशल, अनुभव और प्राथमिकताओं के आधार पर तैयार की गई सिफ़ारिशें'
            : 'Based on your skills, experience and preferences'}
        </p>
      </header>

      {/* Error state if recommendation fetch encountered an issue */}
      {error && (
        <div className="error-banner" role="alert">
          <div>
            <strong>{isHindi ? 'त्रुटि:' : 'Notice:'}</strong> {error}
          </div>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              style={{ textDecoration: 'underline', fontWeight: 600 }}
            >
              {isHindi ? 'पुनः प्रयास करें' : 'Retry'}
            </button>
          )}
        </div>
      )}

      {/* Compact Profile Summary Strip */}
      <section
        className="profile-summary-grid"
        style={{ marginBottom: '2.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
      >
        {profile.current_occupation && (
          <div className="summary-card">
            <div className="summary-card-label">{isHindi ? 'वर्तमान व्यवसाय' : 'Current Occupation'}</div>
            <div className="summary-card-value">
              {profile.current_occupation}
            </div>
          </div>
        )}

        {profile.current_activity && (
          <div className="summary-card">
            <div className="summary-card-label">{isHindi ? 'वर्तमान गतिविधि' : 'Current Activity'}</div>
            <div className="summary-card-value">
              {profile.current_activity}
            </div>
          </div>
        )}

        {(!profile.current_occupation && !profile.current_activity) && (
          <div className="summary-card">
            <div className="summary-card-label">{isHindi ? 'वर्तमान कार्य' : 'Current Work'}</div>
            <div className="summary-card-value">
              {isHindi ? 'उल्लेख नहीं' : 'Not specified'}
            </div>
          </div>
        )}

        {userInterests && (
          <div className="summary-card">
            <div className="summary-card-label">{isHindi ? 'रुचि' : 'Interest'}</div>
            <div className="summary-card-value">
              {userInterests.join(', ')}
            </div>
          </div>
        )}

        {profile.preferred_specialization && (
          <div className="summary-card">
            <div className="summary-card-label">{isHindi ? 'विशेषज्ञता' : 'Specialization'}</div>
            <div className="summary-card-value">
              {profile.preferred_specialization}
            </div>
          </div>
        )}

        <div className="summary-card">
          <div className="summary-card-label">{isHindi ? 'कार्य अनुभव' : 'Experience'}</div>
          <div className="summary-card-value">
            {profile.experience_years !== undefined && profile.experience_years !== null
              ? `${Number(profile.experience_years)} ${isHindi ? 'वर्ष' : 'years'}`
              : isHindi
                ? 'शुरुआती'
                : 'Entry / None'}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">{isHindi ? 'शिक्षा' : 'Education'}</div>
          <div className="summary-card-value">
            {profile.education || (isHindi ? 'उल्लेख नहीं' : 'Not specified')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">{isHindi ? 'स्थान' : 'Location'}</div>
          <div className="summary-card-value">
            {profile.location || (isHindi ? 'उल्लेख नहीं' : 'Not specified')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">{isHindi ? 'कार्य प्राथमिकता' : 'Preference'}</div>
          <div className="summary-card-value">
            {profile.employment_preference
              ? (isHindi
                  ? (profile.employment_preference.toLowerCase().includes('wage')
                      ? 'वेतन रोजगार (नौकरी)'
                      : profile.employment_preference.toLowerCase().includes('self')
                        ? 'स्वरोजगार (व्यवसाय)'
                        : 'लचीला / दोनों')
                  : profile.employment_preference)
              : (isHindi ? 'सामान्य' : 'Flexible')}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-label">{isHindi ? 'कार्य परिवेश' : 'Work Setting'}</div>
          <div className="summary-card-value">
            {profile.mobility_constraint || (isHindi ? 'स्थानीय / लचीला' : 'Local / Flexible')}
          </div>
        </div>

        {userSkills && (
          <div className="summary-card" style={{ gridColumn: '1 / -1' }}>
            <div className="summary-card-label">{isHindi ? 'दर्ज कौशल' : 'Recorded Skills'}</div>
            <div className="summary-card-pills">
              {userSkills.map((s, idx) => (
                <span key={`${s}-${idx}`} className="skill-pill">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Top 3 Recommendations Section */}
      <section className="recommendations-section">
        <div className="recommendations-header-wrap">
          <h2 className="recommendations-title">
            <span>🎯</span>
            <span>
              {isHindi
                ? (recommendations.length > 0 ? `अनुशंसित भूमिकाएं (${recommendations.length})` : 'अनुशंसित भूमिकाएं')
                : (recommendations.length > 0 ? `Recommended Roles (${recommendations.length})` : 'Recommended Roles')}
            </span>
          </h2>
          <p className="recommendations-subtitle">
            {isHindi
              ? 'राष्ट्रीय कौशल योग्यता फ्रेमवर्क (NSQF) के अंतर्गत सरकारी मान्यता प्राप्त भूमिकाएं'
              : 'Accredited government-aligned NSQF vocational pathways matching your background'}
          </p>
        </div>

        {recommendations && recommendations.length > 0 ? (
          <div className="recommendations-list">
            {recommendations.map((rec, index) => {
              const isFirst = index === 0;
              const matchPct = rec.match_percentage || Math.round(rec.match_score * 100);
              const scoreClass = matchPct >= 65 ? 'high' : 'medium';
              const isPrefMismatch = rec.preference_alignment && rec.preference_alignment.toLowerCase().includes('rather than');

              return (
                <article
                  key={rec.role_id}
                  className={`recommendation-card ${isFirst ? 'rank-1' : ''}`}
                  aria-labelledby={`role-title-${rec.role_id}`}
                >
                  {/* Top Bar with Title and Match Badge */}
                  <div className="card-top-bar">
                    <div className="role-title-wrap">
                      <span className="role-rank-badge">
                        #{index + 1} {isHindi ? 'अनुशंसा' : 'Match'}
                      </span>
                      <h3 id={`role-title-${rec.role_id}`} className="role-name">
                        {rec.role_title}
                      </h3>
                      <div className="card-meta-chips">
                        {rec.match_type === 'alternative' && (
                          <span
                            className="chip-pref"
                            style={{
                              background: 'rgba(234, 179, 8, 0.15)',
                              color: '#b45309',
                              border: '1px solid rgba(234, 179, 8, 0.35)',
                              fontWeight: 600,
                            }}
                          >
                            ⚡ {isHindi ? 'वैकल्पिक मार्ग — कौशल आधारित' : 'Alternative Pathway — Skill-based'}
                          </span>
                        )}
                        <span className="chip-sector">{rec.sector}</span>
                        <span className="chip-nsqf">NSQF Level {rec.nsqf_level}</span>
                        <span className="chip-sector" style={{ fontSize: '0.75rem' }}>
                          QP: {rec.pathway?.qp_code || rec.role_id}
                        </span>
                        {rec.preference_alignment && (
                          <span className={`chip-pref ${isPrefMismatch ? 'mismatch' : 'aligned'}`}>
                            {isPrefMismatch ? '⚠️ ' : '✓ '}
                            {rec.preference_alignment}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className={`match-percentage-badge ${scoreClass}`}>
                      <span>★</span>
                      <span>{matchPct}% {isHindi ? 'मैच' : 'Match'}</span>
                    </div>
                  </div>

                  {/* Grounded Explanation */}
                  <div className="role-explanation">
                    <strong>{isHindi ? 'यह भूमिका आपके लिए क्यों उपयुक्त है: ' : 'Why this role matches: '}</strong>
                    {rec.explanation}
                  </div>

                  {/* Skills Comparison: Already Have vs To Develop */}
                  <div className="skills-comparison-grid">
                    {/* Skills already have */}
                    <div className="skills-subgroup">
                      <div className="subgroup-heading have">
                        <span>✓</span>
                        <span>{isHindi ? 'आपके पास मौजूद कौशल' : 'Skills You Already Have'}</span>
                      </div>
                      <div className="pills-cluster">
                        {rec.skills_already_have && rec.skills_already_have.length > 0 ? (
                          rec.skills_already_have.map((skill, sIdx) => (
                            <span key={`have-${skill}-${sIdx}`} className="skill-tag have">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                            {isHindi ? 'फाउंडेशन स्तर से प्रशिक्षण शुरू होगा' : 'Foundation training will cover core basics'}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Skills to develop */}
                    <div className="skills-subgroup">
                      <div className="subgroup-heading gap">
                        <span>▲</span>
                        <span>{isHindi ? 'प्रशिक्षण द्वारा विकसित करने योग्य कौशल' : 'Skills to Develop (Gap)'}</span>
                      </div>
                      <div className="pills-cluster">
                        {rec.skills_to_develop && rec.skills_to_develop.length > 0 ? (
                          rec.skills_to_develop.map((skill, gIdx) => (
                            <span key={`gap-${skill}-${gIdx}`} className="skill-tag gap">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.8rem', color: 'var(--slate-500)' }}>
                            {isHindi ? 'सभी मुख्य कौशल पूरे हैं' : 'All baseline skills demonstrated'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Pathway Roadmap & Certification Details */}
                  {rec.pathway && (
                    <div className="pathway-roadmap-box">
                      <div className="roadmap-header">
                        <span>🎓</span>
                        <span>{isHindi ? 'प्रशिक्षण एवं प्रमाणन मार्ग' : 'Training & Certification Roadmap'}</span>
                      </div>

                      <div className="roadmap-details-grid">
                        <div>
                          <div className="roadmap-item-label">{isHindi ? 'योग्यता प्रमाण पत्र' : 'Qualification'}</div>
                          <div className="roadmap-item-value">{rec.pathway.qualification}</div>
                        </div>

                        <div>
                          <div className="roadmap-item-label">{isHindi ? 'पात्रता' : 'Eligibility'}</div>
                          <div className="roadmap-item-value">{rec.pathway.eligibility}</div>
                        </div>

                        <div>
                          <div className="roadmap-item-label">{isHindi ? 'अवधि / प्रारूप' : 'Duration / Format'}</div>
                          <div className="roadmap-item-value">{rec.pathway.duration}</div>
                        </div>

                        <div>
                          <div className="roadmap-item-label">{isHindi ? 'संबद्ध संस्था' : 'Awarding Body'}</div>
                          <div className="roadmap-item-value">{rec.pathway.organization}</div>
                        </div>
                      </div>

                      {rec.pathway.url && (
                        <a
                          href={rec.pathway.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="pathway-source-link"
                        >
                          <span>🔗</span>
                          <span>{isHindi ? 'आधिकारिक स्रोत एवं विवरण देखें' : 'View official qualification document'}</span>
                        </a>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        ) : (
          <div className="no-matches-card" style={{
            textAlign: 'center',
            padding: '3rem 2rem',
            background: 'var(--slate-50, #f8fafc)',
            borderRadius: '1rem',
            border: '1px dashed var(--slate-300, #cbd5e1)',
            margin: '1.5rem 0'
          }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📋</div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--slate-800, #1e293b)', marginBottom: '0.75rem' }}>
              {isHindi ? 'कोई उपयुक्त व्यावसायिक मार्ग नहीं मिला' : 'No Direct NSQF Pathway Found'}
            </h3>
            <p style={{ color: 'var(--slate-600, #475569)', maxWidth: '540px', margin: '0 auto 1.5rem auto', lineHeight: 1.6 }}>
              {isHindi
                ? 'वर्तमान 23-भूमिका ज्ञान आधार में आपकी पृष्ठभूमि के लिए कोई प्रत्यक्ष सरकारी व्यावसायिक प्रमाणन नहीं मिला। कृपया अपने व्यावहारिक कौशल का अधिक विवरण जोड़कर या संबंधित क्षेत्रों की खोज करके पुनः प्रयास करें।'
                : 'The current curated knowledge base does not contain an accredited short-term NSQF pathway directly matching your stated background. Try exploring related vocational trades or providing additional practical skills.'}
            </p>
          </div>
        )}
      </section>

      {/* Action Buttons */}
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
