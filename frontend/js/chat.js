/**
 * Chat UI — Voice-first with collapsible chat log
 * Manages voice ring states, message rendering, and TTS
 */

let ttsEnabled = true;
let messageCount = 0;

// ── Voice Ring State Management ──

function setVoiceState(state) {
    const ring = document.getElementById('voiceRing');
    const statusText = document.getElementById('voiceStatusText');
    const transcript = document.getElementById('voiceTranscript');
    if (!ring) return;

    ring.className = 'voice-ring ' + state;

    const labels = {
        'listening': '🎤 बोलिए... Speak now',
        'thinking': '🤔 सोच रहा हूँ... Thinking...',
        'speaking': '🔊 सुनिए... Speaking...',
        'idle': '🎤 माइक दबाएं / Tap mic to start',
    };
    if (statusText) statusText.textContent = labels[state] || labels['idle'];
}

function setVoiceTranscript(text) {
    const el = document.getElementById('voiceTranscript');
    if (el) el.textContent = text;
}

// ── Chat Log Toggle ──

function toggleChatLog() {
    const log = document.getElementById('chatLog');
    const btn = document.getElementById('chatToggleBtn');
    if (!log) return;

    const isHidden = log.classList.contains('hidden');
    log.classList.toggle('hidden');
    if (btn) {
        btn.innerHTML = isHidden
            ? '📜 चैट छुपाएं / Hide Chat <span class="msg-count">' + messageCount + '</span>'
            : '📜 चैट देखें / Show Chat <span class="msg-count">' + messageCount + '</span>';
    }
}

function updateMsgCount() {
    messageCount++;
    const el = document.getElementById('msgCount');
    if (el) el.textContent = messageCount;
}

// ── Message Rendering ──

function addUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-user';
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    updateMsgCount();
    scrollToBottom();
}

function addAssistantMessage(text, audioBase64) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-assistant';

    let formattedText = formatMessage(text);
    msgDiv.innerHTML = formattedText;

    // Replay button
    const speakBtn = document.createElement('button');
    speakBtn.className = 'message-audio-btn';
    speakBtn.innerHTML = '🔊 सुनें';
    speakBtn.onclick = () => {
        if (audioBase64) { playAudioWithCallback(audioBase64); }
        else { speakText(text); }
    };
    msgDiv.appendChild(speakBtn);

    chatMessages.appendChild(msgDiv);
    updateMsgCount();
    scrollToBottom();

    // Update voice ring to "speaking" state
    setVoiceState('speaking');
    setVoiceTranscript('');

    // Auto-speak
    if (ttsEnabled) {
        if (audioBase64) {
            playAudioWithCallback(audioBase64);
        } else {
            speakText(text);
        }
    }
}

// ── TTS (Browser fallback) ──

function speakText(text) {
    if (!('speechSynthesis' in window)) {
        setVoiceState('idle');
        if (typeof onTTSComplete === 'function') onTTSComplete();
        return;
    }

    window.speechSynthesis.cancel();
    setVoiceState('speaking');

    let cleanText = text
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/#{1,3}\s/g, '')
        .replace(/^- /gm, '')
        .replace(/^\d+\.\s/gm, '')
        .replace(/[🏛️✅❌🎤⚠️🚨📋💰🔊🤔📜🙏]/g, '')
        .replace(/---.*?---/gs, '')
        .trim();

    const chunks = splitIntoChunks(cleanText, 180);

    chunks.forEach((chunk, i) => {
        const utterance = new SpeechSynthesisUtterance(chunk);
        const hasHindi = /[\u0900-\u097f]/.test(chunk);
        utterance.lang = hasHindi ? 'hi-IN' : 'en-IN';
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        const voices = window.speechSynthesis.getVoices();
        const langPrefix = hasHindi ? 'hi' : 'en';
        const v = voices.find(v => v.lang.startsWith(langPrefix) && v.lang.includes('IN'));
        if (v) utterance.voice = v;

        if (i === chunks.length - 1) {
            utterance.onend = () => {
                setVoiceState('idle');
                if (typeof onTTSComplete === 'function') onTTSComplete();
            };
        }

        window.speechSynthesis.speak(utterance);
    });
}

function splitIntoChunks(text, maxLen) {
    const sentences = text.match(/[^.!?।\n]+[.!?।\n]?/g) || [text];
    const chunks = [];
    let current = '';
    for (const s of sentences) {
        if ((current + s).length > maxLen && current.length > 0) {
            chunks.push(current.trim());
            current = s;
        } else {
            current += s;
        }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
}

// ── Audio Playback (Polly) ──

function playAudioWithCallback(base64Data) {
    const audio = document.getElementById('audioPlayer');
    audio.src = 'data:audio/mp3;base64,' + base64Data;
    setVoiceState('speaking');

    audio.onended = () => {
        setVoiceState('idle');
        if (typeof onTTSComplete === 'function') onTTSComplete();
    };
    audio.onerror = () => {
        setVoiceState('idle');
        if (typeof onTTSComplete === 'function') onTTSComplete();
    };

    audio.play().catch(err => {
        console.log('Audio play failed:', err);
        setVoiceState('idle');
        if (typeof onTTSComplete === 'function') onTTSComplete();
    });
}

function playAudio(base64Data) {
    const audio = document.getElementById('audioPlayer');
    audio.src = 'data:audio/mp3;base64,' + base64Data;
    audio.play().catch(err => console.log('Audio play failed:', err));
}

// ── TTS Toggle ──

function toggleTTS() {
    ttsEnabled = !ttsEnabled;
    window.speechSynthesis.cancel();
    const btn = document.getElementById('ttsToggle');
    if (btn) {
        btn.innerHTML = ttsEnabled ? '🔊' : '🔇';
        btn.title = ttsEnabled ? 'Voice ON' : 'Voice OFF';
    }
}

// ── Typing Indicator ──

function showTypingIndicator() {
    setVoiceState('thinking');
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    chatMessages.appendChild(typingDiv);
}

function removeTypingIndicator() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

// ── Message Formatting ──

function formatMessage(text) {
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*(?!\*)(.*?)\*(?!\*)/g, '<em>$1</em>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
    html = html.replace(/((?:<li>.*?<\/li>\n?)+)/g, '<ul>$1</ul>');
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');

    return html;
}

// ── Scroll ──

function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

// Preload voices
if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
