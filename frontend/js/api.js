/**
 * API Client — Handles all API calls to the LokSarthi backend
 */

// API base URL — will be set after deployment
// For local dev: http://localhost:8000
// For AWS: https://<api-id>.execute-api.<region>.amazonaws.com/prod
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : (window.API_URL || '/api');

/**
 * Send a chat message to the backend
 */
async function apiChat(message, sessionId, language) {
    const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: message,
            session_id: sessionId,
            language: language || null,
        }),
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
}

/**
 * Send voice audio to the backend
 */
async function apiVoice(audioBase64, sessionId, language) {
    const response = await fetch(`${API_BASE}/api/voice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            audio_base64: audioBase64,
            session_id: sessionId,
            language: language || 'hi',
        }),
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
}

/**
 * Get list of all schemes
 */
async function apiGetSchemes() {
    const response = await fetch(`${API_BASE}/api/schemes`);
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
}

/**
 * Health check
 */
async function apiHealthCheck() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        return response.ok;
    } catch {
        return false;
    }
}
