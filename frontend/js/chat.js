/**
 * Chat UI — Handles message rendering and chat interactions
 */

/**
 * Add a user message to the chat
 */
function addUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-user';
    msgDiv.textContent = text;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

/**
 * Add an assistant message with optional audio playback
 */
function addAssistantMessage(text, audioBase64) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message message-assistant';

    // Format text — convert markdown-like formatting
    let formattedText = formatMessage(text);

    msgDiv.innerHTML = formattedText;

    // Add audio play button if audio exists
    if (audioBase64) {
        const audioBtn = document.createElement('button');
        audioBtn.className = 'message-audio-btn';
        audioBtn.innerHTML = '🔊 सुनें / Listen';
        audioBtn.onclick = () => playAudio(audioBase64);
        msgDiv.appendChild(audioBtn);
    }

    chatMessages.appendChild(msgDiv);
    scrollToBottom();

    // Auto-play audio for accessibility (voice-first)
    if (audioBase64) {
        playAudio(audioBase64);
    }
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    chatMessages.appendChild(typingDiv);
    scrollToBottom();
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator() {
    const typing = document.getElementById('typingIndicator');
    if (typing) typing.remove();
}

/**
 * Format message text with basic markdown support
 */
function formatMessage(text) {
    // Escape HTML
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text*
    html = html.replace(/(?<!\*)\*(?!\*)(.*?)\*(?!\*)/g, '<em>$1</em>');

    // Headers: ### heading
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');

    // Bullet points
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li>.*?<\/li>\n?)+)/g, '<ul>$1</ul>');

    // Line breaks
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');

    // Emoji highlighting for alerts
    html = html.replace(/🚨/g, '<span style="font-size:20px">🚨</span>');
    html = html.replace(/⚠️/g, '<span style="font-size:20px">⚠️</span>');
    html = html.replace(/✅/g, '<span style="font-size:18px">✅</span>');

    return html;
}

/**
 * Play audio from base64 string
 */
function playAudio(base64Data) {
    const audio = document.getElementById('audioPlayer');
    audio.src = 'data:audio/mp3;base64,' + base64Data;
    audio.play().catch(err => console.log('Audio play failed:', err));
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
        window.scrollTo(0, document.body.scrollHeight);
    }, 100);
}
