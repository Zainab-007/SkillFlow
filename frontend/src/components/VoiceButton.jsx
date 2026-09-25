import React from 'react';

/**
 * VoiceButton component.
 * Displays microphone toggle with distinct states: Idle, Listening, Processing.
 *
 * @param {Object} props
 * @param {boolean} props.isListening
 * @param {boolean} props.isProcessing
 * @param {boolean} props.isSupported
 * @param {boolean} props.disabled
 * @param {function(): void} props.onToggle
 * @param {string} [props.language='en']
 */
export default function VoiceButton({
  isListening,
  isProcessing,
  isSupported,
  disabled = false,
  onToggle,
  language = 'en',
}) {
  const isHindi = language === 'hi';

  const getLabel = () => {
    if (!isSupported) {
      return isHindi ? 'आवाज इनपुट उपलब्ध नहीं है' : 'Voice input not available';
    }
    if (isProcessing) {
      return isHindi ? '⏳ समझ रहे हैं...' : '⏳ Processing...';
    }
    if (isListening) {
      return isHindi ? '🔴 सुन रहे हैं... (रोकने के लिए दबाएं)' : '🔴 Listening... (Tap to finish)';
    }
    return isHindi ? '🎤 बोलने के लिए दबाएं' : '🎤 Tap to speak';
  };

  const getAriaLabel = () => {
    if (!isSupported) return 'Voice input not supported';
    if (isListening) return 'Stop listening';
    if (isProcessing) return 'Processing speech';
    return 'Start voice input';
  };

  return (
    <div className="mic-button-wrapper">
      <button
        type="button"
        id="skillflow-mic-btn"
        className={`mic-button ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''}`}
        onClick={onToggle}
        disabled={disabled || !isSupported}
        aria-label={getAriaLabel()}
        title={getLabel()}
      >
        {isListening ? (
          <span style={{ fontSize: '1.75rem' }}>⏹</span>
        ) : isProcessing ? (
          <span style={{ fontSize: '1.75rem' }}>⏳</span>
        ) : (
          <span>🎤</span>
        )}
      </button>

      <span className={`mic-label ${isListening ? 'listening' : ''}`}>
        {getLabel()}
      </span>

      {!isSupported && (
        <span className="mic-unsupported-note">
          {isHindi
            ? 'इस ब्राउज़र में आवाज़ इनपुट समर्थित नहीं है। आप नीचे अपना उत्तर लिख सकते हैं।'
            : "Voice input isn't supported in this browser. You can type your answer instead."}
        </span>
      )}
    </div>
  );
}
