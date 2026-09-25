import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import VoiceButton from './VoiceButton';

/**
 * ConversationPanel component.
 * Manages the active assistant question, scrollable dialogue history,
 * microphone interaction, and fallback text input.
 *
 * @param {Object} props
 * @param {string} props.assistantQuestion - Current question from assistant
 * @param {Array<{role: string, content: string}>} props.conversationHistory
 * @param {boolean} props.isLoading - Backend request in progress
 * @param {boolean} props.isSpeaking - TTS audio currently playing
 * @param {boolean} props.voiceEnabled - TTS enabled toggle state
 * @param {function(): void} props.onToggleVoice - Toggle TTS
 * @param {function(string): void} props.onSendMessage - Send user text/speech
 * @param {string} [props.language='en']
 * @param {string} [props.error]
 * @param {function(): void} [props.onClearError]
 * @param {boolean} props.isSpeechSupported
 * @param {boolean} props.isListening
 * @param {boolean} props.isSpeechProcessing
 * @param {function(): void} props.onToggleSpeech
 * @param {string} [props.inputText] - Current draft text in input
 * @param {function(string): void} [props.onInputChange] - Text change handler
 */
export default function ConversationPanel({
  assistantQuestion,
  conversationHistory = [],
  isLoading = false,
  isSpeaking = false,
  voiceEnabled = true,
  onToggleVoice,
  onSendMessage,
  language = 'en',
  error = null,
  onClearError,
  isSpeechSupported,
  isListening,
  isSpeechProcessing,
  onToggleSpeech,
  inputText,
  onInputChange,
}) {
  const [localInputText, setLocalInputText] = useState('');
  const historyEndRef = useRef(null);
  const isHindi = language === 'hi';

  const currentInputText =
    inputText !== undefined && onInputChange ? inputText : localInputText;

  const handleTextChange = (val) => {
    if (onInputChange) {
      onInputChange(val);
    } else {
      setLocalInputText(val);
    }
  };

  // Auto-scroll conversation history to bottom as turns accumulate
  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory, assistantQuestion]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!currentInputText.trim() || isLoading) return;
    const textToSend = currentInputText.trim();
    handleTextChange('');
    onSendMessage(textToSend);
  };

  return (
    <div className="conversation-card">
      {/* Error alert if any */}
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          {onClearError && (
            <button type="button" onClick={onClearError} aria-label="Dismiss error">
              &times;
            </button>
          )}
        </div>
      )}

      {/* Active Assistant Question Card */}
      <section className="assistant-active-question-card" aria-live="polite">
        <div className="active-q-header">
          <span className="assistant-badge">
            {isHindi ? 'स्किलफ्लो सहायक' : 'SkillFlow Assistant'}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {isSpeaking && (
              <span className="audio-status-pill">
                🔊 {isHindi ? 'बोल रहे हैं...' : 'Speaking...'}
              </span>
            )}
            <button
              type="button"
              className={`voice-toggle-btn ${voiceEnabled ? 'active' : ''}`}
              onClick={onToggleVoice}
              title={
                voiceEnabled
                  ? (isHindi ? 'आवाज़ बंद करें' : 'Mute voice responses')
                  : (isHindi ? 'आवाज़ चालू करें' : 'Enable voice responses')
              }
            >
              {voiceEnabled
                ? (isHindi ? '🔊 आवाज़ चालू' : '🔊 Voice On')
                : (isHindi ? '🔇 आवाज़ बंद' : '🔇 Voice Off')}
            </button>
          </div>
        </div>

        <p className="active-q-text">
          {assistantQuestion ||
            (isHindi
              ? 'नमस्ते! अपने काम या कौशल के बारे में बताएं...'
              : 'Tell me a little about the work you currently do.')}
        </p>
      </section>

      {/* Visible Conversation History */}
      {conversationHistory.length > 0 && (
        <div
          className="chat-history-stream"
          aria-label="Conversation history"
          role="log"
        >
          {conversationHistory.map((turn, idx) => (
            <ChatMessage
              key={`${idx}-${turn.role}`}
              role={turn.role}
              content={turn.content}
              language={language}
            />
          ))}
          <div ref={historyEndRef} />
        </div>
      )}

      {/* Interaction Area: Voice Mic + Text Fallback */}
      <div className="interaction-area">
        <VoiceButton
          isListening={isListening}
          isProcessing={isSpeechProcessing || isLoading}
          isSupported={isSpeechSupported}
          disabled={isLoading}
          onToggle={onToggleSpeech}
          language={language}
        />

        <div
          style={{
            width: '100%',
            textAlign: 'center',
            color: 'var(--slate-400)',
            fontSize: '0.85rem',
          }}
        >
          {isHindi ? '— अथवा लिखकर भेजें —' : '— or review/type your answer below —'}
        </div>

        {/* Text fallback input: shows spoken words live, allows editing, and sends on click */}
        <form onSubmit={handleSubmit} className="text-input-row">
          <input
            type="text"
            id="skillflow-text-input"
            className="text-fallback-input"
            value={currentInputText}
            onChange={(e) => handleTextChange(e.target.value)}
            placeholder={
              isHindi
                ? 'अपना उत्तर यहाँ बोलें या लिखें...'
                : 'Type your answer here or speak above...'
            }
            disabled={isLoading}
            aria-label="Your answer input"
          />
          <button
            type="submit"
            id="skillflow-send-btn"
            className="btn-send"
            disabled={!currentInputText.trim() || isLoading}
            aria-label="Send message"
          >
            <span>{isHindi ? 'भेजें' : 'Send'}</span>
            <span>➔</span>
          </button>
        </form>
      </div>
    </div>
  );
}
