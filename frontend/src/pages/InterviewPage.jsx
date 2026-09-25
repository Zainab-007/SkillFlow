import React, { useState, useEffect, useRef, useCallback } from 'react';
import ConversationPanel from '../components/ConversationPanel';
import ProfileProgress from '../components/ProfileProgress';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { useTextToSpeech } from '../hooks/useTextToSpeech';
import { sendConversationTurn } from '../services/api';

/**
 * InterviewPage component.
 * Core conversational interface for the AI livelihood assessment.
 *
 * @param {Object} props
 * @param {string} props.sessionId - Current session identifier
 * @param {string} props.language - 'en' or 'hi'
 * @param {function(Object): void} props.onInterviewComplete - Called when interview finishes
 * @param {function(): void} props.onReset
 */
export default function InterviewPage({
  sessionId,
  language = 'en',
  onInterviewComplete,
  onReset,
}) {
  const [conversationHistory, setConversationHistory] = useState([]);
  const [assistantQuestion, setAssistantQuestion] = useState('');
  const [profile, setProfile] = useState({});
  const [fieldsCompleted, setFieldsCompleted] = useState([]);
  const [fieldsRemaining, setFieldsRemaining] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [inputText, setInputText] = useState('');

  const initialTurnTriggered = useRef(false);
  const completionTimeoutRef = useRef(null);
  const isHindi = language === 'hi';

  // Cleanup pending completion timeout on unmount
  useEffect(() => {
    return () => {
      if (completionTimeoutRef.current) {
        clearTimeout(completionTimeoutRef.current);
      }
    };
  }, []);

  // Text-To-Speech hook
  const {
    isSupported: isTtsSupported,
    voiceEnabled,
    isSpeaking,
    speak,
    toggleVoice,
    stopSpeaking,
  } = useTextToSpeech({ language, defaultEnabled: true });

  // Handle incoming speech recognition transcript:
  // Fills the text input so the user can review and edit before sending.
  const handleTranscript = useCallback((recognizedText) => {
    if (recognizedText !== undefined && recognizedText !== null) {
      setInputText(recognizedText);
    }
  }, []);

  // Speech Recognition hook
  const {
    isSupported: isSpeechSupported,
    isListening,
    isProcessing: isSpeechProcessing,
    error: speechError,
    startListening,
    stopListening,
    clearError: clearSpeechError,
  } = useSpeechRecognition({
    language,
    onTranscript: handleTranscript,
  });

  const toggleSpeech = () => {
    if (isListening) {
      stopListening();
    } else {
      stopSpeaking(); // stop any assistant audio if user wants to speak
      clearSpeechError();
      startListening();
    }
  };

  // Central message dispatcher
  const handleSendMessage = async (userMessage) => {
    if (!userMessage || !userMessage.trim() || isLoading) return;

    if (completionTimeoutRef.current) {
      clearTimeout(completionTimeoutRef.current);
    }

    stopSpeaking();
    setIsLoading(true);
    setApiError(null);
    setInputText(''); // Clear input box once message is submitted

    // Optimistically update conversation history in the UI
    const updatedHistory = [
      ...conversationHistory,
      { role: 'user', content: userMessage },
    ];
    setConversationHistory(updatedHistory);

    try {
      const data = await sendConversationTurn({
        sessionId,
        language,
        message: userMessage,
        conversationHistory: updatedHistory,
      });

      // Update state with backend response
      setAssistantQuestion(data.assistant_question);
      setProfile(data.profile || {});
      setFieldsCompleted(data.fields_completed || []);
      setFieldsRemaining(data.fields_remaining || []);

      // Add assistant response to history
      const finalHistory = [
        ...updatedHistory,
        { role: 'assistant', content: data.assistant_question },
      ];
      setConversationHistory(finalHistory);

      // Speak assistant question if TTS is enabled
      if (data.assistant_question) {
        speak(data.assistant_question);
      }

      // Check for interview completion: navigate ONLY when data.interview_complete is true
      if (data.interview_complete) {
        if (completionTimeoutRef.current) {
          clearTimeout(completionTimeoutRef.current);
        }
        completionTimeoutRef.current = setTimeout(() => {
          onInterviewComplete(data.profile || {});
        }, 3000);
      }
    } catch (err) {
      setApiError(err.message || 'Something went wrong while connecting to SkillFlow.');
    } finally {
      setIsLoading(false);
    }
  };

  // Kick off the initial turn upon entering the interview
  useEffect(() => {
    if (initialTurnTriggered.current) return;
    initialTurnTriggered.current = true;

    const initialGreeting = isHindi
      ? 'नमस्ते, मुझे काम और प्रशिक्षण के अवसरों के बारे में जानना है।'
      : 'Hello, I want to explore livelihood and training opportunities.';

    setIsLoading(true);
    sendConversationTurn({
      sessionId,
      language,
      message: initialGreeting,
      conversationHistory: [],
    })
      .then((data) => {
        setAssistantQuestion(data.assistant_question);
        setProfile(data.profile || {});
        setFieldsCompleted(data.fields_completed || []);
        setFieldsRemaining(data.fields_remaining || []);

        setConversationHistory([
          { role: 'assistant', content: data.assistant_question },
        ]);

        if (data.assistant_question) {
          speak(data.assistant_question);
        }
      })
      .catch((err) => {
        setApiError(err.message || 'Could not connect to SkillFlow backend.');
        const fallbackQ = isHindi
          ? 'नमस्ते! मुझे अपने वर्तमान काम या कौशल के बारे में कुछ बताएं।'
          : 'Hello! Tell me a little about the work you currently do or skills you have.';
        setAssistantQuestion(fallbackQ);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [sessionId, language, isHindi, speak]);

  const activeError = apiError || speechError;
  const handleClearError = () => {
    setApiError(null);
    clearSpeechError();
  };

  return (
    <div className="interview-layout">
      <ConversationPanel
        assistantQuestion={assistantQuestion}
        conversationHistory={conversationHistory}
        isLoading={isLoading}
        isSpeaking={isSpeaking}
        voiceEnabled={voiceEnabled}
        onToggleVoice={toggleVoice}
        onSendMessage={handleSendMessage}
        language={language}
        error={activeError}
        onClearError={handleClearError}
        isSpeechSupported={isSpeechSupported}
        isListening={isListening}
        isSpeechProcessing={isSpeechProcessing}
        onToggleSpeech={toggleSpeech}
        inputText={inputText}
        onInputChange={setInputText}
      />

      <ProfileProgress
        fieldsCompleted={fieldsCompleted}
        fieldsRemaining={fieldsRemaining}
        language={language}
      />
    </div>
  );
}
