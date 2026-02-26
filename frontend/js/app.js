/**
 * App.js — Main application logic for LokSarthi
 */

// State
let sessionId = generateSessionId();
let currentLanguage = 'hi';
let isChatActive = false;

/**
 * Initialize the app
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set up language selector
    const langSelect = document.getElementById('languageSelector');
    langSelect.addEventListener('change', (e) => {
        currentLanguage = e.target.value;
    });

    // Focus input on desktop
    if (window.innerWidth > 768) {
        document.getElementById('messageInput').focus();
    }

    console.log('🏛️ LokSarthi initialized — Session:', sessionId);
});

/**
 * Generate a random session ID
 */
function generateSessionId() {
    return 'ls_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
}

/**
 * Start a specific service from hero cards
 */
function startService(service) {
    switchToChat();

    const prompts = {
        schemes: {
            hi: 'मुझे सरकारी योजनाओं के बारे में जानना है। मैं कौन सी योजनाओं का लाभ उठा सकता/सकती हूँ?',
            en: 'I want to know about government schemes. Which schemes am I eligible for?',
        },
        rti: {
            hi: 'मुझे RTI दर्ज करनी है। एक शिकायत है।',
            en: 'I want to file an RTI application. I have a complaint.',
        },
        finance: {
            hi: 'मुझे लोन और पैसों के बारे में सलाह चाहिए।',
            en: 'I need advice about loans and finances.',
        },
    };

    const prompt = prompts[service]?.[currentLanguage] || prompts[service]?.['en'] || '';
    if (prompt) {
        sendMessageText(prompt);
    }
}

/**
 * Switch to chat view
 */
function switchToChat() {
    const hero = document.getElementById('heroSection');
    const chat = document.getElementById('chatSection');
    const backBtn = document.getElementById('backBtn');

    hero.classList.add('hidden');
    chat.classList.remove('hidden');
    backBtn.classList.remove('hidden');
    isChatActive = true;

    document.getElementById('messageInput').focus();
}

/**
 * Go back to home
 */
function goHome() {
    const hero = document.getElementById('heroSection');
    const chat = document.getElementById('chatSection');
    const backBtn = document.getElementById('backBtn');

    hero.classList.remove('hidden');
    chat.classList.add('hidden');
    backBtn.classList.add('hidden');
    isChatActive = false;

    // Clear chat
    document.getElementById('chatMessages').innerHTML = '';

    // Reset session
    sessionId = generateSessionId();
}

/**
 * Handle Enter key in input
 */
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * Send message from input field
 */
function sendMessage() {
    const input = document.getElementById('messageInput');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    sendMessageText(text);
}

/**
 * Send a message text to the API
 */
async function sendMessageText(text) {
    if (!isChatActive) {
        switchToChat();
    }

    // Add user message to chat
    addUserMessage(text);

    // Show typing indicator
    showTypingIndicator();

    // Show loading
    showLoading(true);

    try {
        // Call API
        const result = await apiChat(text, sessionId, currentLanguage);

        // Remove typing
        removeTypingIndicator();
        showLoading(false);

        // Update language if detected
        if (result.language) {
            currentLanguage = result.language;
            document.getElementById('languageSelector').value = result.language;
        }

        // Add assistant response
        addAssistantMessage(result.text, result.audio_base64);

    } catch (error) {
        removeTypingIndicator();
        showLoading(false);
        console.error('Chat error:', error);

        // Show error message
        addAssistantMessage(
            currentLanguage === 'hi'
                ? '❌ सर्वर से कनेक्ट नहीं हो पाया। कृपया बाद में कोशिश करें।\n\nError: ' + error.message
                : '❌ Could not connect to server. Please try again later.\n\nError: ' + error.message,
            null
        );
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}
