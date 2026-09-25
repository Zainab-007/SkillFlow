import React from 'react';

/**
 * ChatMessage component.
 * Renders an exchange bubble in the conversation stream.
 *
 * @param {Object} props
 * @param {'assistant' | 'user'} props.role
 * @param {string} props.content
 * @param {string} [props.language='en']
 */
export default function ChatMessage({ role, content, language = 'en' }) {
  const isAssistant = role === 'assistant';
  const isHindi = language === 'hi';

  const authorLabel = isAssistant
    ? isHindi
      ? 'स्किलफ्लो सहायक'
      : 'SkillFlow Assistant'
    : isHindi
      ? 'आप'
      : 'You';

  return (
    <div className={`chat-bubble ${isAssistant ? 'assistant' : 'user'}`}>
      <div className="chat-bubble-author">{authorLabel}</div>
      <div className="chat-bubble-text">{content}</div>
    </div>
  );
}
