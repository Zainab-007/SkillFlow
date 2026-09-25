import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for browser-based speech recognition using the Web Speech API.
 *
 * @param {Object} options
 * @param {string} options.language - 'en' or 'hi'
 * @param {function(string): void} [options.onTranscript] - Called as transcript updates (interim and final)
 * @param {function(string): void} [options.onResult] - Called with final transcript
 * @param {function(string): void} [options.onError] - Called with an error message
 */
export function useSpeechRecognition({
  language = 'en',
  onTranscript,
  onResult,
  onError,
}) {
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const onTranscriptRef = useRef(onTranscript);
  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // Check Web Speech API support in browser
  const SpeechRecognition =
    typeof window !== 'undefined'
      ? window.SpeechRecognition || window.webkitSpeechRecognition
      : null;

  const isSupported = Boolean(SpeechRecognition);

  // Log support status on mount
  useEffect(() => {
    console.debug('[SkillFlow STT] supported', isSupported);
  }, [isSupported]);

  // Clean up recognition instance on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.warn('Error stopping speech recognition:', err);
      }
    }
  }, []);

  const startListening = useCallback(() => {
    if (!isSupported) {
      const msg =
        "Voice input isn't supported in this browser. You can type your answer instead.";
      console.error('[SkillFlow STT] error:', msg);
      setError(msg);
      if (onErrorRef.current) onErrorRef.current(msg);
      return;
    }

    // Abort any existing instance to prevent InvalidStateError in Chrome
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }

    try {
      console.debug('[SkillFlow STT] starting');
      setError(null);
      setTranscript('');

      const recognition = new SpeechRecognition();
      recognition.continuous = false; // Single utterance
      recognition.interimResults = true; // Stream interim results to UI
      recognition.maxAlternatives = 1;

      // Set regional language: en-IN or hi-IN
      recognition.lang = language === 'hi' ? 'hi-IN' : 'en-IN';

      recognition.onstart = () => {
        console.debug('[SkillFlow STT] listening');
        setIsListening(true);
        setIsProcessing(false);
        setError(null);
      };

      recognition.onresult = (event) => {
        let accumulated = '';
        let hasFinal = false;

        for (let i = 0; i < event.results.length; i++) {
          const item = event.results[i];
          accumulated += item[0].transcript;
          if (item.isFinal) {
            hasFinal = true;
          }
        }

        const recognizedText = accumulated.trim();
        console.debug('[SkillFlow STT] result:', recognizedText);

        setTranscript(recognizedText);

        // Notify parent to populate text input
        if (onTranscriptRef.current && recognizedText) {
          onTranscriptRef.current(recognizedText);
        }

        if (hasFinal && onResultRef.current && recognizedText) {
          onResultRef.current(recognizedText);
        }
      };

      recognition.onerror = (event) => {
        console.error('[SkillFlow STT] error:', event.error);
        setIsListening(false);
        setIsProcessing(false);

        // Do not treat clean user abort as an alarming error
        if (event.error === 'aborted') {
          return;
        }

        let userMsg = '';
        switch (event.error) {
          case 'not-allowed':
          case 'permission-denied':
            userMsg =
              'Microphone permission was denied. Please allow microphone access in your browser or type your answer.';
            break;
          case 'no-speech':
            userMsg =
              'No speech was detected. Tap the microphone and try speaking again.';
            break;
          case 'network':
            userMsg =
              'Speech recognition network error. You can type your answer instead.';
            break;
          default:
            userMsg = `Voice recognition error (${event.error}). Please type your answer.`;
        }

        setError(userMsg);
        if (onErrorRef.current) {
          onErrorRef.current(userMsg);
        }
      };

      recognition.onend = () => {
        console.debug('[SkillFlow STT] ended');
        setIsListening(false);
        setIsProcessing(false);
        recognitionRef.current = null;
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('[SkillFlow STT] error:', err);
      setIsListening(false);
      setIsProcessing(false);
      const msg = `Could not start microphone: ${err.message || err}`;
      setError(msg);
      if (onErrorRef.current) onErrorRef.current(msg);
    }
  }, [isSupported, language]);

  return {
    isSupported,
    isListening,
    isProcessing,
    transcript,
    error,
    startListening,
    stopListening,
    clearError: () => setError(null),
  };
}
