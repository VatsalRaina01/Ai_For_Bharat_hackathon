/**
 * Voice Module — Continuous voice conversation mode
 * Speak → Listen → Reply → Speak back → Listen again (loop)
 * Text input is optional — voice is primary.
 */

let recognition = null;
let isRecording = false;
let conversationMode = false;  // Continuous voice loop
let silenceTimer = null;
const SILENCE_TIMEOUT = 2500;  // Auto-send after 2.5s of silence

// Language codes for Web Speech API (BCP-47)
const SPEECH_LANG_MAP = {
    'hi': 'hi-IN',
    'en': 'en-IN',
    'ta': 'ta-IN',
    'te': 'te-IN',
    'bn': 'bn-IN',
    'mr': 'mr-IN',
    'gu': 'gu-IN',
    'kn': 'kn-IN',
    'ml': 'ml-IN',
    'pa': 'pa-IN',
};

/**
 * Check if Web Speech API is supported
 */
function isSpeechSupported() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
}

/**
 * Create a new speech recognition instance
 */
function createRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRecognition();

    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.lang = SPEECH_LANG_MAP[currentLanguage] || 'hi-IN';

    return rec;
}

/**
 * Toggle voice — starts conversation mode on first tap
 */
function toggleVoice() {
    if (!isSpeechSupported()) {
        alert('आपका ब्राउज़र वॉइस सपोर्ट नहीं करता। Chrome या Edge उपयोग करें।\n\nPlease use Chrome or Edge for voice.');
        return;
    }

    if (isRecording) {
        // User tapped mic to stop — exit conversation mode
        conversationMode = false;
        stopRecording();
    } else {
        // Start conversation mode
        conversationMode = true;
        startRecording();
    }
}

/**
 * Start speech recognition with silence detection
 */
function startRecording() {
    // Cancel any ongoing TTS first (so mic doesn't pick up speaker)
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }

    recognition = createRecognition();
    let fullTranscript = '';
    let permissionTimer = null;

    const input = document.getElementById('messageInput');
    input.placeholder = '🎤 माइक अनुमति दें... Allow mic...';

    recognition.onresult = (event) => {
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                fullTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }

        // Show live preview in input AND voice transcript
        const currentText = (fullTranscript + interimTranscript).trim();
        input.value = currentText;
        input.placeholder = '🎤 सुन रहा हूँ... Listening...';
        if (typeof setVoiceTranscript === 'function') setVoiceTranscript(currentText);

        // Reset silence timer — user is still speaking
        clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            // User went silent for 2.5s — auto-send
            const text = input.value.trim();
            if (text) {
                autoSendVoiceMessage(text);
                input.value = '';
                fullTranscript = '';
            }
        }, SILENCE_TIMEOUT);
    };

    recognition.onend = () => {
        clearTimeout(silenceTimer);

        if (isRecording) {
            // Auto-restart if still in recording mode
            try {
                recognition.start();
            } catch (e) {
                console.log('Restart failed:', e);
                isRecording = false;
                conversationMode = false;
                updateMicButtons(false);
            }
            return;
        }

        // User manually stopped
        const text = input.value.trim();
        if (text) {
            autoSendVoiceMessage(text);
            input.value = '';
        }
        input.placeholder = 'अपना सवाल लिखें... Type your question...';
        updateMicButtons(false);
    };

    recognition.onerror = (event) => {
        console.log('Speech error:', event.error);
        clearTimeout(permissionTimer);

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            isRecording = false;
            conversationMode = false;
            updateMicButtons(false);
            input.placeholder = 'अपना सवाल लिखें... Type your question...';
            alert('माइक्रोफ़ोन अनुमति दें।\nAllow microphone access.\n\n🔒 Address bar → Allow microphone.');
            return;
        }
        // Non-fatal: let onend restart
    };

    recognition.onstart = () => {
        clearTimeout(permissionTimer);
        isRecording = true;
        updateMicButtons(true);
        if (typeof setVoiceState === 'function') setVoiceState('listening');
        input.placeholder = '🎤 बोलिए... Speak now...';

        if (typeof isChatActive !== 'undefined' && !isChatActive) {
            switchToChat();
        }
    };

    try {
        recognition.start();
    } catch (e) {
        console.error('Start failed:', e);
        input.placeholder = 'अपना सवाल लिखें... Type your question...';
        return;
    }

    permissionTimer = setTimeout(() => {
        if (!isRecording) {
            input.placeholder = '⚠️ ब्राउज़र में माइक अनुमति दें! Allow mic in browser!';
        }
    }, 3000);
}

/**
 * Stop speech recognition
 */
function stopRecording() {
    clearTimeout(silenceTimer);
    isRecording = false;
    if (recognition) {
        try { recognition.stop(); } catch (e) { /* ignore */ }
    }
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
}

/**
 * Auto-send voice message and pause mic while processing
 */
function autoSendVoiceMessage(text) {
    // Pause mic while AI processes and speaks back
    isRecording = false;
    if (recognition) {
        try { recognition.stop(); } catch (e) { /* ignore */ }
    }
    updateMicButtons(false);

    const input = document.getElementById('messageInput');
    input.placeholder = '🤔 सोच रहा हूँ... Thinking...';
    if (typeof setVoiceState === 'function') setVoiceState('thinking');
    if (typeof setVoiceTranscript === 'function') setVoiceTranscript('');

    // Send the message through the normal chat flow
    sendMessageText(text);
}

/**
 * Called by chat.js when TTS finishes speaking the response
 * Restarts mic for the next turn of conversation
 */
function onTTSComplete() {
    if (conversationMode) {
        // Small delay to avoid echo, then restart listening
        setTimeout(() => {
            if (conversationMode) {
                startRecording();
            }
        }, 500);
    }
}

/**
 * Update mic button visuals
 */
function updateMicButtons(recording) {
    const heroMic = document.getElementById('heroMicBtn');
    const chatMic = document.getElementById('micBtn');

    if (heroMic) {
        heroMic.classList.toggle('recording', recording);
        heroMic.classList.toggle('pulse', !recording);
    }
    if (chatMic) {
        chatMic.classList.toggle('recording', recording);
    }

    // Update conversation mode indicator
    const indicator = document.getElementById('voiceModeIndicator');
    if (indicator) {
        indicator.classList.toggle('hidden', !conversationMode);
    }
}
