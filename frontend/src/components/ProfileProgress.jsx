import React from 'react';

// Human-friendly mapping for internal profile keys
const FIELD_LABELS = {
  current_occupation: {
    en: 'Current work',
    hi: 'वर्तमान कार्य',
  },
  experience_years: {
    en: 'Experience',
    hi: 'कार्य अनुभव',
  },
  skills: {
    en: 'Skills',
    hi: 'कौशल एवं हुनर',
  },
  interests: {
    en: 'Interests',
    hi: 'रुचियां / क्षेत्र',
  },
  education: {
    en: 'Education',
    hi: 'शिक्षा स्तर',
  },
  employment_preference: {
    en: 'Work preference',
    hi: 'रोजगार प्राथमिकता',
  },
  location: {
    en: 'Location',
    hi: 'स्थान / शहर',
  },
  mobility_constraint: {
    en: 'Work setting',
    hi: 'कार्य परिवेश',
  },
};

const DISPLAY_ORDER = [
  'current_occupation',
  'experience_years',
  'skills',
  'interests',
  'education',
  'employment_preference',
  'location',
  'mobility_constraint',
];

/**
 * ProfileProgress component.
 * Displays human-friendly progress indicators for collected profile fields.
 *
 * @param {Object} props
 * @param {string[]} props.fieldsCompleted
 * @param {string[]} props.fieldsRemaining
 * @param {string} [props.language='en']
 */
export default function ProfileProgress({
  fieldsCompleted = [],
  fieldsRemaining = [],
  language = 'en',
}) {
  const isHindi = language === 'hi';
  const completedSet = new Set(fieldsCompleted);

  return (
    <aside className="profile-sidebar" aria-label="Profile progress tracker">
      <h3 className="sidebar-title">
        {isHindi ? 'आपकी प्रोफ़ाइल' : 'Your Profile'}
      </h3>
      <p className="sidebar-desc">
        {isHindi
          ? 'बातचीत के साथ जानकारी स्वतः दर्ज हो रही है'
          : 'Information captured through conversation'}
      </p>

      <ul className="progress-list">
        {DISPLAY_ORDER.map((fieldKey) => {
          const isDone = completedSet.has(fieldKey);
          const labels = FIELD_LABELS[fieldKey] || { en: fieldKey, hi: fieldKey };
          const label = isHindi ? labels.hi : labels.en;

          return (
            <li
              key={fieldKey}
              className={`progress-item ${isDone ? 'completed' : 'pending'}`}
            >
              <span className={`progress-icon ${isDone ? 'done' : 'pending'}`}>
                {isDone ? '✓' : '○'}
              </span>
              <span>{label}</span>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
