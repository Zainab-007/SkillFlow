/**
 * Centralized API client for the SkillFlow frontend.
 *
 * Talks to the FastAPI backend running at http://localhost:8000
 * (or via the Vite proxy configured at /api).
 */

const API_BASE = '/api';

/**
 * Send one turn of conversation to the backend.
 *
 * @param {Object} params
 * @param {string} params.sessionId - Unique session identifier
 * @param {string} params.language - 'en' or 'hi'
 * @param {string} params.message - User's latest utterance / text
 * @param {Array<{role: string, content: string}>} [params.conversationHistory=[]]
 * @returns {Promise<{
 *   session_id: string,
 *   assistant_question: string,
 *   profile_update: Object,
 *   profile: Object,
 *   fields_completed: string[],
 *   fields_remaining: string[],
 *   interview_complete: boolean
 * }>}
 */
export async function sendConversationTurn({
  sessionId,
  language = 'en',
  message,
  conversationHistory = [],
}) {
  const payload = {
    session_id: sessionId,
    language,
    message: message.trim(),
    conversation_history: conversationHistory,
  };

  let response;
  try {
    response = await fetch(`${API_BASE}/conversation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (netErr) {
    throw new Error(
      'Could not connect to the SkillFlow server. Please check that the backend is running on http://localhost:8000.'
    );
  }

  if (!response.ok) {
    let errorDetail = 'Something went wrong while connecting to SkillFlow.';
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Use fallback
    }

    if (response.status === 503) {
      throw new Error(
        'The conversation service is temporarily unavailable: Gemini API key is not configured.'
      );
    } else if (response.status === 502) {
      throw new Error(
        'The conversation service encountered an error communicating with AI. Please try again.'
      );
    } else if (response.status === 400) {
      throw new Error(errorDetail);
    } else {
      throw new Error(`Server error (${response.status}): ${errorDetail}`);
    }
  }

  return response.json();
}

/**
 * Check backend health status.
 *
 * @returns {Promise<{status: string, service: string}>}
 */
export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) return { status: 'error', service: 'SkillFlow backend' };
    return res.json();
  } catch {
    return { status: 'offline', service: 'SkillFlow backend' };
  }
}

/**
 * Fetch top 3 NSQF recommendations and training pathways for a completed profile.
 *
 * @param {Object} profile - Completed livelihood profile
 * @returns {Promise<{
 *   total_evaluated: number,
 *   total_recommended: number,
 *   recommendations: Array<Object>
 * }>}
 */
export async function fetchRecommendations(profile) {
  let response;
  try {
    response = await fetch(`${API_BASE}/recommendations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ profile }),
    });
  } catch (netErr) {
    throw new Error(
      'Could not connect to the recommendations service. Please verify that the backend is running.'
    );
  }

  if (!response.ok) {
    let errorDetail = 'Failed to fetch recommendations.';
    try {
      const errJson = await response.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // fallback
    }
    throw new Error(`Recommendations error (${response.status}): ${errorDetail}`);
  }

  return response.json();
}

