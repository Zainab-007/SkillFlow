import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for browser-based text-to-speech using SpeechSynthesis API.
 *
 * @param {Object} options
 * @param {string} options.language - 'en' or 'hi'
 * @param {boolean} [options.defaultEnabled=true] - Initial voice on/off state
 */
export function useTextToSpeech({ language = 'en', defaultEnabled = true }) {
  const [voiceEnabled, setVoiceEnabled] = useState(defaultEnabled);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState([]);

  const isSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const currentUtteranceRef = useRef(null);

  // Load and cache voices when available
  useEffect(() => {
    if (!isSupported) return;

    const updateVoices = () => {
      const available = window.speechSynthesis.getVoices();
      if (available && available.length > 0) {
        setVoices(available);
      }
    };

    updateVoices();
    window.speechSynthesis.onvoiceschanged = updateVoices;

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, [isSupported]);

  // Pick the most suitable voice based on language
  const selectVoice = useCallback(
    (lang) => {
      if (!voices.length) return null;

      const targetLang = lang === 'hi' ? 'hi-IN' : 'en-IN';

      // 1. Exact regional match (e.g. hi-IN or en-IN)
      let matched = voices.find(
        (v) => v.lang && v.lang.toLowerCase() === targetLang.toLowerCase()
      );

      // 2. Language prefix match (e.g. hi or en)
      if (!matched) {
        const prefix = lang === 'hi' ? 'hi' : 'en';
        matched = voices.find(
          (v) => v.lang && v.lang.toLowerCase().startsWith(prefix)
        );
      }

      // 3. Fallback to default voice
      if (!matched) {
        matched = voices.find((v) => v.default) || voices[0];
      }

      return matched;
    },
    [voices]
  );

  const stopSpeaking = useCallback(() => {
    if (isSupported && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch (err) {
        console.warn('SpeechSynthesis cancel error:', err);
      }
      setIsSpeaking(false);
    }
  }, [isSupported]);

  const speak = useCallback(
    (text) => {
      if (!isSupported || !voiceEnabled || !text) return;

      try {
        // Cancel any currently speaking utterance first
        stopSpeaking();

        const utterance = new SpeechSynthesisUtterance(text);
        const selectedVoice = selectVoice(language);

        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }

        utterance.lang = language === 'hi' ? 'hi-IN' : 'en-IN';
        utterance.rate = 0.95; // Slightly slower for clarity in voice guidance
        utterance.pitch = 1.0;

        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = (e) => {
          // 'canceled' or 'interrupted' errors are normal when a user interrupts or toggles
          if (e.error !== 'canceled' && e.error !== 'interrupted') {
            console.warn('SpeechSynthesis utterance error:', e);
          }
          setIsSpeaking(false);
        };

        currentUtteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn('SpeechSynthesis speak failed gracefully:', err);
        setIsSpeaking(false);
      }
    },
    [isSupported, voiceEnabled, language, selectVoice, stopSpeaking]
  );

  const toggleVoice = useCallback(() => {
    setVoiceEnabled((prev) => {
      const next = !prev;
      if (!next) {
        stopSpeaking();
      }
      return next;
    });
  }, [stopSpeaking]);

  return {
    isSupported,
    voiceEnabled,
    isSpeaking,
    speak,
    stopSpeaking,
    toggleVoice,
  };
}
